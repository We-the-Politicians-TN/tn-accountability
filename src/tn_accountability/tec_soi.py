"""Statements of Disclosure of Interests (SS-8004) from the Tennessee Ethics Commission.

    python -m tn_accountability.tec_soi fetch --years 2021-2026
    python -m tn_accountability.tec_soi load
    python -m tn_accountability.tec_soi match      # propose filer -> legislator links

The only per-member disclosure Tennessee publishes: outside income, directorships,
investments, sponsored travel, lobbying ties, retainers, loans and leadership PACs.
Filed annually under penalty of perjury. See docs/influence_channels.md.

Fetch: the public search (conflict.app.tn.gov) is a session-bound form POST that
redirects to a paginated results page, 25 per page. One search per (position, year),
then every filing's HTML is saved under data/raw/tec/soi/ with a SHA-256 in the
manifest. Existing files are never rewritten — they are evidence.

Load: each filing is <h2>Section</h2> followed by either the word None or
<fieldset><legend>Part A</legend><p>line<br/>line<br/>qualifier</p>... blocks. The
parser keeps every item's lines exactly as published beside the parsed columns.

Match: filers are attributed to legislators the same way TREF filers are (D67-D69):
surname-dominant scoring, discounted by how close the runner-up is, restricted to the
filer's chamber. Nothing is attributed until approved.
"""

from __future__ import annotations

import argparse
import hashlib
from urllib.parse import parse_qs
import json
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import requests
from rapidfuzz import fuzz

from . import config
from .backfill import parse_years
from .legiscan import log

BASE = "https://conflict.app.tn.gov/conflict"
POSITIONS = ("Representative", "Senator")
RAW = config.RAW_DIR / "tec" / "soi"
UA = "tn-accountability/0.1 (public records research; github.com/We-the-Politicians-TN/tn-accountability)"
DELAY = (0.8, 1.6)

SECTION_ORDER = [
    "Sources of Income", "Positions Held", "Blind Trust", "Investments",
    "Legislative Expenses", "Lobbying", "Professional Services", "Retainer Fees",
    "Bankruptcy", "Loans", "Services to State Entities", "Leadership PACs",
]


def _retrying(fn, what, attempts=6):
    """apps.tn.gov drops TLS connections routinely; see D104 for why this catches
    the RequestException base rather than a list of subclasses."""
    last = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except requests.exceptions.RequestException as exc:
            if isinstance(exc, requests.exceptions.HTTPError):
                st = exc.response.status_code if exc.response is not None else None
                if st is not None and st < 500 and st != 429:
                    raise
            last = exc
            if attempt == attempts:
                break
            wait = min(60, 3 * 2 ** attempt) + random.uniform(0, 2)
            print(f"    {what}: {type(exc).__name__}, retry {attempt}/{attempts-1} in {wait:.0f}s")
            time.sleep(wait)
    raise RuntimeError(f"{what} failed after {attempts} attempts: {last}")


def _sleep():
    time.sleep(random.uniform(*DELAY))


# --- fetch --------------------------------------------------------------------

def search_body(position: str, year: int) -> dict:
    # Exactly what the browser form serialises. The app validates the whole form,
    # local fields included, and the checkbox marker must be 'visible'.
    return {
        "stateFirstName": "", "stateLastName": "", "position": position,
        "stateYear": str(year), "_stateCanOnly": "visible", "stateSearch": "Search",
        "localFirstName": "", "localLastName": "", "localPosition": "", "county": "",
        "localYear": str(year), "_localCanOnly": "visible",
    }


ROW_RE = re.compile(r'<tr[^>]*>(.*?)</tr>', re.S)
LINK_RE = re.compile(r'href="(view_form_(8004|8005)\.htm\?[^"]+)"[^>]*>(.*?)</a>', re.S)
CELL_RE = re.compile(r'<td[^>]*>(.*?)</td>', re.S)
BANNER_RE = re.compile(r'(\d+) users? found')


def _clean(x: str) -> str:
    x = re.sub(r'<[^>]+>', ' ', x)
    x = x.replace('&amp;', '&').replace('&#39;', "'").replace('&quot;', '"')
    return re.sub(r'\s+', ' ', x).strip()


def parse_listing(html: str) -> list:
    out = []
    for r in ROW_RE.findall(html):
        m = LINK_RE.search(r)
        if not m:
            continue
        cells = [_clean(c) for c in CELL_RE.findall(r)]
        href = m.group(1).replace('&amp;', '&')
        # parse_qs tolerates stray or empty segments; a hand-rolled split crashed
        # the first bulk run on one link with a segment lacking '='.
        qs = {k: v[0] for k, v in parse_qs(href.split('?', 1)[1], keep_blank_values=True).items()}
        if 'id' not in qs or 'f' not in qs:
            continue
        q = qs
        out.append(dict(
            name_raw=_clean(m.group(3)), position=cells[1] if len(cells) > 1 else '',
            form_label=cells[2] if len(cells) > 2 else '',
            form=f"SS-{m.group(2)}", amended='Amended' in (cells[2] if len(cells) > 2 else ''),
            filer_id=int(q['id']), form_id=int(q['f']), version=int(q.get('v', 1)),
            href=href))
    return out


def fetch(years, positions=POSITIONS, forms=("SS-8004",)) -> dict:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    totals = dict(listings=0, filings=0, skipped=0)
    for position in positions:
        for year in years:
            d = RAW / position.lower() / str(year)
            d.mkdir(parents=True, exist_ok=True)
            log(f"{position} {year}: searching")
            s.cookies.clear()
            _retrying(lambda: s.get(f"{BASE}/search.htm", timeout=60).raise_for_status(), "init")
            _sleep()
            r = _retrying(lambda: s.post(f"{BASE}/search.htm", data=search_body(position, year),
                                         timeout=90, allow_redirects=True), "search")
            r.raise_for_status()
            pages = [r.text]
            m = BANNER_RE.search(_clean(r.text))
            total = int(m.group(1)) if m else 0
            npages = (total + 24) // 25
            for p in range(2, npages + 1):
                _sleep()
                rp = _retrying(lambda p=p: s.get(f"{BASE}/results.htm?d-49809-p={p}", timeout=90),
                               f"page {p}")
                rp.raise_for_status()
                pages.append(rp.text)
            for i, html in enumerate(pages, 1):
                (d / f"results_p{i}.html").write_text(html)
            totals["listings"] += len(pages)

            rows = [x for pg in pages for x in parse_listing(pg)]
            rows = [x for x in rows if x["form"] in forms]
            log(f"  {total} listed, {len(rows)} {'/'.join(forms)} filings")
            manifest = []
            for x in rows:
                fn = d / f"{x['filer_id']}_f{x['form_id']}_v{x['version']}.html"
                if fn.exists():
                    totals["skipped"] += 1
                else:
                    _sleep()
                    rf = _retrying(lambda x=x: s.get(f"{BASE}/{x['href']}", timeout=90),
                                   f"filing {x['name_raw']}")
                    rf.raise_for_status()
                    fn.write_text(rf.text)
                    totals["filings"] += 1
                x["file"] = fn.name
                x["sha256"] = hashlib.sha256(fn.read_bytes()).hexdigest()
                x["url"] = f"{BASE}/{x['href']}"
                manifest.append(x)
            (d / "_manifest.json").write_text(json.dumps(dict(
                position=position, year=year, fetched_at=datetime.now(timezone.utc).isoformat(),
                listed=total, filings=manifest), indent=2))
    log(f"done: {totals['filings']} filings fetched, {totals['skipped']} already on disk, "
        f"{totals['listings']} listing pages")
    return totals


# --- parse a filing -------------------------------------------------------------

H2_RE = re.compile(r'<h2>\s*(.*?)\s*</h2>', re.S)
FIELDSET_RE = re.compile(r'<fieldset>(.*?)</fieldset>', re.S)
LEGEND_RE = re.compile(r'<legend>\s*Part\s+([AB])\s*</legend>', re.S)
P_RE = re.compile(r'<p[^>]*>(.*?)</p>', re.S)
AMOUNT_RE = re.compile(r'\$\s?([\d,]+(?:\.\d{1,2})?)')


def _items_from_block(block: str) -> list:
    items = []
    block = re.sub(r'<legend>.*?</legend>', ' ', block, flags=re.S)
    for p in P_RE.findall(block):
        lines = [_clean(l) for l in re.split(r'<br\s*/?>', p)]
        lines = [l for l in lines if l]
        if not lines:
            continue
        items.append(lines)
    if not items:
        t = _clean(block)
        if t and t.lower() != 'none':
            items.append([t])
    return items


def parse_filing(html: str) -> dict:
    """The page is a flat sequence of <h2> chunks. The first three carry the header
    (Report Year, Date of Filing, Filer Contact Information); the rest are the
    disclosure sections. Everything before the first <h2> is page chrome."""
    out = dict(sections={}, filer_name_raw=None, position_raw=None, address_raw=None,
               report_year=None, filed_date=None, tec_filer_id=None)
    for chunk in re.split(r'<h2>', html)[1:]:
        title, _, body = chunk.partition('</h2>')
        title = _clean(title)
        if title == 'Report Year':
            m = re.search(r'(20\d{2})', _clean(body)); out["report_year"] = int(m.group(1)) if m else None
        elif title == 'Date of Filing':
            m = re.search(r'(\d{4}-\d{2}-\d{2})', _clean(body)); out["filed_date"] = m.group(1) if m else None
        elif title == 'Filer Contact Information':
            m = re.search(r'<strong>(.*?)</strong>', body, re.S)
            out["filer_name_raw"] = _clean(m.group(1)) if m else None
            m = re.search(r'dashboard\.htm\?id=(\d+)', body)
            out["tec_filer_id"] = int(m.group(1)) if m else None
            after = body.split('View all statements</a>', 1)[1] if 'View all statements</a>' in body else body
            lines = [_clean(l) for l in re.split(r'<br\s*/?>', after)]
            lines = [l for l in lines if l]
            out["position_raw"] = lines[0] if lines else None
            out["address_raw"] = ', '.join(lines[1:]) if len(lines) > 1 else None
        elif title in SECTION_ORDER:
            items = []
            fieldsets = FIELDSET_RE.findall(body)
            if fieldsets:
                for fs in fieldsets:
                    lm = LEGEND_RE.search(fs)
                    for lines in _items_from_block(fs):
                        items.append((lm.group(1) if lm else None, lines))
            else:
                for lines in _items_from_block(body):
                    items.append((None, lines))
            out["sections"][title] = items
    return out


# --- load ----------------------------------------------------------------------

def norm_name(n: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'[^A-Za-z .\'-]', ' ', n or '')).strip().upper()


def load(conn) -> None:
    manifests = sorted(RAW.glob("*/*/_manifest.json"))
    if not manifests:
        log("nothing fetched yet"); return
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO data_pulls (source, search_type, source_files, notes)
                       VALUES ('tn_ethics_commission','soi_ss8004',%s,%s) RETURNING id""",
                    ([str(m.relative_to(config.PROJECT_ROOT)) for m in manifests],
                     f"load of {len(manifests)} SS-8004 listing manifests"))
        pull_id = cur.fetchone()[0]
    n_disc = n_items = n_skip = 0
    for mpath in manifests:
        man = json.loads(mpath.read_text())
        d = mpath.parent
        for x in man["filings"]:
            f = d / x["file"]
            parsed = parse_filing(f.read_text())
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM disclosures WHERE tec_form_id=%s AND version=%s",
                            (x["form_id"], x["version"]))
                if cur.fetchone():
                    n_skip += 1; continue
                pos = parsed.get("position_raw") or x["position"]
                chamber = "house" if pos.lower().startswith("rep") else ("senate" if pos.lower().startswith("sen") else None)
                cur.execute("""INSERT INTO disclosures (tec_filer_id, tec_form_id, version, form, amended,
                                 report_year, filer_name_raw, filer_name, position_raw, chamber, address_raw,
                                 filed_date, source_file, sha256, source_url, data_pull_id)
                               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::chamber,%s,%s,%s,%s,%s,%s) RETURNING id""",
                            (x["filer_id"], x["form_id"], x["version"], x["form"], x["amended"],
                             parsed.get("report_year") or man["year"], x["name_raw"], norm_name(x["name_raw"]),
                             pos, chamber, parsed.get("address_raw"), parsed.get("filed_date"),
                             str(f.relative_to(config.PROJECT_ROOT)), x["sha256"], x["url"], pull_id))
                did = cur.fetchone()[0]
                n_disc += 1
                rows = []
                for section, items in parsed["sections"].items():
                    for seq, (part, lines) in enumerate(items, 1):
                        qual, body = None, []
                        for l in lines:
                            qm = re.search(r'\b(Income received by|Held by|Furnished by|Loan Recipient|Lobbyist Relation to Filer)\s*:?\s*(.*)$', l, re.I)
                            if qm:
                                qual = (qm.group(1) + ': ' + qm.group(2)).strip(': ').strip()
                                pre = l[:qm.start()].strip(' ,;')
                                if pre:
                                    body.append(pre)
                            else:
                                body.append(l)
                        am = AMOUNT_RE.search(' '.join(lines))
                        rows.append((did, section, part, seq, ' | '.join(lines),
                                     body[0] if body else None, body[1] if len(body) > 1 else None,
                                     qual, float(am.group(1).replace(',', '')) if am else None))
                if rows:
                    cur.executemany("""INSERT INTO disclosure_items (disclosure_id, section, part, seq,
                                         lines_raw, name, detail, qualifier, amount)
                                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""", rows)
                    n_items += len(rows)
        conn.commit()
    with conn.cursor() as cur:
        cur.execute("UPDATE data_pulls SET status='success', finished_at=now(), rows_added=%s WHERE id=%s",
                    (n_disc + n_items, pull_id))
    conn.commit()
    log(f"loaded {n_disc} filings, {n_items} items; {n_skip} already loaded")


# --- match filers to legislators ----------------------------------------------

def _score(filer: str, leg: dict) -> int:
    toks = filer.replace('.', ' ').split()
    if not toks:
        return 0
    f_last = toks[-1]; f_given = [t for t in toks[:-1] if len(t) > 1]
    l_last = (leg["last_name"] or "").upper()
    last_s = int(fuzz.ratio(f_last, l_last)) if l_last else 0
    if last_s < 85:
        return min(last_s, 60)
    known = {v.upper() for v in (leg["first_name"], leg["nickname"], leg["middle_name"]) if v}
    if not known or not f_given:
        given_s = 55
    else:
        given_s = max(int(fuzz.ratio(t, k)) for t in f_given for k in known)
        if any(t == k for t in f_given for k in known):
            given_s = max(given_s, 97)
        # JOHN vs JOHNNY, TIM vs TIMOTHY: a prefix is strong evidence
        if any(k.startswith(t) or t.startswith(k) for t in f_given for k in known if min(len(t), len(k)) >= 3):
            given_s = max(given_s, 90)
        # ED -> EDWARD: a two-letter prefix is enough when the surname is exact.
        if last_s == 100 and any(k.startswith(t) for t in f_given for k in known if len(t) == 2):
            given_s = max(given_s, 88)
    return int(round(last_s * 0.65 + given_s * 0.35))


def match(conn, auto_score=92, auto_margin=15) -> None:
    with conn.cursor() as cur:
        cur.execute("""SELECT id, full_name_raw, first_name, middle_name, last_name, nickname, chamber::text
                       FROM legislators WHERE last_name IS NOT NULL""")
        cols = [c[0] for c in cur.description]
        legs = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.execute("""SELECT id, filer_name, chamber::text, report_year FROM disclosures
                       WHERE approved_by IS NULL""")
        discs = cur.fetchall()
        auto = review = 0
        for did, name, chamber, year in discs:
            # Chamber is a preference, not a filter. LegiScan's 114th data lists
            # Sen. London Lamar as House while the Ethics Commission lists her as
            # Senator; a hard filter found her no candidate at all (D110).
            def sc(l):
                base = _score(name, l)
                return base if (not chamber or l["chamber"] == chamber) else max(0, base - 8)
            scored = sorted(((sc(l), l) for l in legs), key=lambda t: -t[0])
            if not scored or scored[0][0] < 70:
                cur.execute("UPDATE disclosures SET legislator_id=NULL, match_confidence=NULL, "
                            "match_method='no candidate >= 70', approved=false WHERE id=%s", (did,))
                review += 1; continue
            best_s, best = scored[0]
            second = scored[1][0] if len(scored) > 1 else 0
            margin = best_s - second
            conf = round(max(0.0, best_s - max(0, auto_margin - margin) * 2.0), 2)
            ok = best_s >= auto_score and margin >= auto_margin
            note = "" if best["chamber"] == chamber else f" CHAMBER MISMATCH filer={chamber} legiscan={best['chamber']}"
            cur.execute("""UPDATE disclosures SET legislator_id=%s, match_confidence=%s,
                             match_method=%s, approved=%s WHERE id=%s""",
                        (best["id"], conf, f"fuzzy raw={best_s} margin={margin}{note}", ok and not note, did))
            auto += ok; review += (not ok)
    conn.commit()
    log(f"matched: {auto} auto-approved, {review} need review")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch"); f.add_argument("--years", default="2021-2026")
    f.add_argument("--positions", default=",".join(POSITIONS))
    sub.add_parser("load"); sub.add_parser("match")
    a = p.parse_args(argv)
    if a.cmd == "fetch":
        fetch(parse_years(a.years), [x.strip() for x in a.positions.split(",") if x.strip()])
        return 0
    with psycopg.connect(config.require("DATABASE_URL")) as conn:
        conn.autocommit = False
        (load if a.cmd == "load" else match)(conn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
