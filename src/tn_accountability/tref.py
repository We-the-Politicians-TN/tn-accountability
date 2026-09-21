"""Fetch raw campaign finance CSVs from the Tennessee Registry of Election Finance.

TREF's search app has no bulk export. The only way to get the full record set is
the path the Accountability Project used for their own Tennessee dataset: submit
the public search form one year at a time and download the CSV export, following
a server-side cursor for results beyond the first page.

Ported from `state/tn/contribs/docs/get_tn_contribs.R` in
irworkshop/accountability_datacleaning, updated for the app's move from
/tncamp-app/ to /tncamp/.

The flow, per year:

    GET  cesearch.htm        establish a session (the cursor lives in it)
    POST cesearch.htm        submit the search; the response IS batch 1's results
    GET  <csv link>          download batch 1 as CSV
    GET  ceresultsnext.htm   advance the server-side cursor to batch 2
    GET  <csv link>          download batch 2 ... repeat while "More" is present

The CSV export returns the entire current batch, not just the 50 rows shown on
screen, so one download per batch is enough. Batch sizes vary (~750-800 rows
observed), so the totals come from the files, never from the page banner.

Downloaded files are written under `data/raw/tref/<run-date>/` and never
modified afterward. They are the evidence trail.
"""

from __future__ import annotations

import hashlib
import random
import re
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from . import config

BASE = "https://apps.tn.gov/tncamp/public"
SEARCH_URL = f"{BASE}/cesearch.htm"
RESULTS_URL = f"{BASE}/ceresults.htm"
NEXT_URL = f"{BASE}/ceresultsnext.htm"

USER_AGENT = (
    "tn-accountability/0.1 (public records research; "
    "github.com/We-the-Politicians-TN/tn-accountability)"
)

# Be a good citizen on a state government server: pause between every request,
# and longer between years. These are deliberately conservative.
PAGE_DELAY = (1.0, 3.0)
YEAR_DELAY = (10.0, 30.0)

# Guard against an unbounded loop if the "More" button never disappears.
# A page cap cannot distinguish a genuinely large year from an infinite loop.
# 2023 tripped the old cap of 500 with 500 *distinct* pages, because TREF served
# ~346 rows/page that year against ~800-890 for other years. The real loop signal
# is the same page arriving twice, which is checked separately below; this cap is
# now only a last-resort stop.
MAX_PAGES_PER_YEAR = 5000


class TrefError(RuntimeError):
    """The TREF site returned something we did not expect."""


def _select_all_fields(search_type: str) -> dict:
    """Request every available output column, so the raw CSV is complete.

    The form exposes different column checkboxes depending on whether you are
    searching contributions or expenditures; sending an irrelevant one is
    harmless, but being explicit documents what each export contains.
    """
    common = {
        "typeField": "true",
        "adjustmentField": "true",
        "amountField": "true",
        "dateField": "true",
        "electionYearField": "true",
        "reportNameField": "true",
    }
    if search_type == "contributions":
        return {
            **common,
            "recipientNameField": "true",
            "contributorNameField": "true",
            "contributorAddressField": "true",
            "contributorOccupationField": "true",
            "contributorEmployerField": "true",
            "descriptionField": "true",
        }
    return {
        **common,
        "candidatePACNameField": "true",
        "vendorNameField": "true",
        "vendorAddressField": "true",
        "purposeField": "true",
        "candidateForField": "true",
        "soField": "true",
    }


# The four contributor types partition the result set: every contribution comes from
# exactly one of them, so searching each separately and combining covers the year
# without overlap. Used when a year is too large to page through in one session.
CONTRIBUTOR_TYPES = ("fromCandidate", "fromPAC", "fromIndividual", "fromOrganization")


def _form_body(search_type: str, year: int, only_from: str = None) -> dict:
    """Build the search form.

    `only_from` restricts to a single contributor type. TREF holds the paging cursor
    in server-side session state, and for a large year that state gives out part way
    through — 2023 failed twice, once after 500 pages and once with an HTTP 500.
    Splitting the year into four disjoint searches keeps each session short enough to
    survive, and the four together are exactly the whole year.
    """
    if search_type not in ("contributions", "expenditures"):
        raise ValueError(f"search_type must be contributions or expenditures, got {search_type!r}")
    if only_from and only_from not in CONTRIBUTOR_TYPES:
        raise ValueError(f"only_from must be one of {CONTRIBUTOR_TYPES}, got {only_from!r}")
    from_flags = {t: ("true" if (only_from is None or t == only_from) else "false")
                  for t in CONTRIBUTOR_TYPES}
    return {
        "searchType": search_type,
        "toType": "both",          # to candidates and committees
        **from_flags,
        "toCandidate": "true",
        "toPac": "true",
        "toOther": "true",
        "electionYearSelection": "",
        "yearSelection": str(year),
        # No name/amount filters — we want the whole year.
        "recipientName": "",
        "contributorName": "",
        "employer": "",
        "occupation": "",
        "zipCode": "",
        "candName": "",
        "vendorName": "",
        "vendorZipCode": "",
        "purpose": "",
        "typeOf": "all",
        "amountSelection": "equal",
        "amountDollars": "",
        "amountCents": "",
        **_select_all_fields(search_type),
        "_continue": "Search",
    }


@dataclass
class ResultsPage:
    """What one results page tells us."""

    row_count: int | None
    csv_url: str | None
    has_more: bool


def _parse_results(html: str) -> ResultsPage:
    soup = BeautifulSoup(html, "lxml")

    link = soup.select_one(".exportlinks a[href]")
    csv_url = None
    if link:
        href = link["href"]
        csv_url = href if href.startswith("http") else f"https://apps.tn.gov{href}"

    # The banner reads "754 results found, displaying 1 to 50." — take only the
    # first number. Concatenating every digit yields nonsense like 754150.
    banner = soup.select_one(".pagebanner")
    row_count = None
    if banner:
        m = re.search(r"([\d,]+)\s+results? found", banner.get_text())
        if m:
            row_count = int(m.group(1).replace(",", ""))

    return ResultsPage(
        row_count=row_count,
        csv_url=csv_url,
        has_more=soup.select_one(".btn-blue") is not None,
    )


@dataclass
class YearResult:
    year: int
    search_type: str
    files: list = field(default_factory=list)
    row_count_reported: int = 0

    @property
    def bytes_downloaded(self) -> int:
        return sum(p.stat().st_size for p in self.files if p.exists())


class TrefClient:
    """A session against the TREF public search app."""

    def __init__(self, out_dir: Path | None = None, delay: bool = True):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.delay = delay
        run_date = date.today().isoformat()
        self.out_dir = out_dir or (config.RAW_DIR / "tref" / run_date)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def _pause(self, bounds: tuple) -> None:
        if self.delay:
            time.sleep(random.uniform(*bounds))

    def _retrying(self, fn, what: str, attempts: int = 6):
        """Retry transient failures with backoff.

        Catches `RequestException`, the common base of every transport failure
        requests raises. Listing individual subclasses was tried and failed three
        times: first HTTPError escaped (raise_for_status sat outside this wrapper),
        then ChunkedEncodingError escaped — it inherits from RequestException, not
        ConnectionError — and discarded 532 successfully downloaded batches because
        batch 533 ended prematurely.

        Over a run of thousands of requests against apps.tn.gov, every one of these
        is a certainty rather than a possibility. The only failure worth surfacing
        immediately is a 4xx, which means our request is wrong and repeating it
        would repeat the mistake.
        """
        last = None
        for attempt in range(1, attempts + 1):
            try:
                return fn()
            except requests.exceptions.RequestException as exc:
                if isinstance(exc, requests.exceptions.HTTPError):
                    status = exc.response.status_code if exc.response is not None else None
                    if status is not None and status < 500 and status != 429:
                        raise           # our request is wrong; retrying changes nothing
                    detail = f"HTTP {status}"
                    base = 5            # server trouble deserves more room
                else:
                    detail = type(exc).__name__
                    base = 2
                last = exc
                if attempt == attempts:
                    break
                backoff = min(90, base * 2 ** attempt) + random.uniform(0, 3)
                print(f"    {what}: {detail}, retry {attempt}/{attempts - 1} in {backoff:.1f}s")
                time.sleep(backoff)
        raise TrefError(f"{what} failed after {attempts} attempts: {last}") from last

    def fetch_year(self, search_type: str, year: int, only_from: str = None) -> YearResult:
        """Download every CSV page for one search type and year.

        `only_from` restricts to one contributor type, for years too large to page
        through in a single session. See `fetch_year_partitioned`.
        """
        result = YearResult(year=year, search_type=search_type)

        # A fresh session per year: the result cursor is server-side state, and
        # reusing a session across years risks inheriting a stale cursor.
        self.session.cookies.clear()
        self._retrying(lambda: self.session.get(SEARCH_URL, timeout=60).raise_for_status(),
                       f"session init {search_type} {year}")

        # The POST redirects to ceresults.htm, so its body is already batch 1.
        def _post():
            # raise_for_status must happen INSIDE the retry: called outside, an
            # HTTP 500 is raised after _retrying has already returned, so the
            # retry logic never sees it. That is what killed 2023 twice.
            r = self.session.post(SEARCH_URL,
                                  data=_form_body(search_type, year, only_from),
                                  timeout=180)
            r.raise_for_status()
            return r

        post = self._retrying(
            _post, f"search {search_type} {year}" + (f" [{only_from}]" if only_from else ""))
        page = _parse_results(post.text)

        if page.csv_url is None:
            # A year with no matching records has no export link. Distinguish that
            # from a layout change by checking whether the page reported a count:
            # "0 results found" is an empty year, a missing banner is a broken parse.
            if page.row_count == 0:
                return result
            raise TrefError(
                f"no CSV export link found for {search_type} {year} "
                f"(reported row count: {page.row_count}). The site layout may have "
                "changed — re-check the selectors in _parse_results()."
            )

        # Real loop detection: if the server hands back a page we have already
        # downloaded, the cursor is not advancing. Comparing content is reliable
        # where counting pages is not.
        seen_digests = set()

        for page_no in range(1, MAX_PAGES_PER_YEAR + 1):
            if page.row_count:
                result.row_count_reported += page.row_count

            suffix = f"-{only_from[4:].lower()}" if only_from else ""
            path = self.out_dir / f"tn_{search_type}_{year}{suffix}-{page_no:03d}.csv"
            if path.exists():
                raise TrefError(f"refusing to overwrite existing raw file: {path}")

            self._pause(PAGE_DELAY)
            csv_url = page.csv_url

            def _download():
                tmp = path.with_suffix(".partial")
                with self.session.get(csv_url, stream=True, timeout=300) as resp:
                    resp.raise_for_status()
                    ctype = resp.headers.get("Content-Type", "")
                    if "csv" not in ctype.lower():
                        raise TrefError(f"expected CSV, got Content-Type {ctype!r}")
                    with open(tmp, "wb") as fh:
                        for chunk in resp.iter_content(chunk_size=1 << 16):
                            fh.write(chunk)
                # Only move into place once the download completed, so a failed
                # attempt never leaves a truncated file in the evidence trail.
                tmp.replace(path)

            self._retrying(_download, f"csv {search_type} {year} batch {page_no}")

            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest in seen_digests:
                path.unlink()
                raise TrefError(
                    f"{search_type} {year}: batch {page_no} is byte-identical to a page "
                    f"already downloaded. The 'More' cursor is not advancing, so this "
                    f"would loop forever. Stopping with {len(result.files)} good batches."
                )
            seen_digests.add(digest)
            result.files.append(path)

            if not page.has_more:
                break

            self._pause(PAGE_DELAY)
            def _next():
                r = self.session.get(NEXT_URL, timeout=120)
                r.raise_for_status()
                return r

            nxt = self._retrying(_next, f"next {search_type} {year} batch {page_no + 1}")
            page = _parse_results(nxt.text)
            if page.csv_url is None:
                raise TrefError(f"lost the CSV link while paging {search_type} {year}")
        else:
            raise TrefError(
                f"{search_type} {year} exceeded {MAX_PAGES_PER_YEAR} pages — "
                "the 'More' button may never be clearing. Stopping rather than looping."
            )

        return result
