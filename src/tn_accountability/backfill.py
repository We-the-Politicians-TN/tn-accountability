"""Resumable bulk download of TREF campaign finance records.

Run this yourself, detached, and leave it alone. A full backfill takes hours;
it is designed so that dying halfway costs you only the year in progress.

    python -m tn_accountability.backfill --years 2019-2026
    python -m tn_accountability.backfill --years 2002-2026 --types contributions
    python -m tn_accountability.backfill --years 2019-2026 --dry-run

Layout:

    data/raw/tref/backfill/<type>/<year>/          a completed year
    data/raw/tref/backfill/<type>/<year>/_manifest.json
    data/raw/tref/backfill/<type>/<year>.partial/  a year still downloading

A year is complete when its directory holds `_manifest.json`. Completed
directories are evidence and are never rewritten — rerunning skips them. A
`.partial` directory is working state, not evidence: it is discarded and
re-fetched, because TREF's paging cursor lives in a server session that cannot
be resumed from the middle.

The manifest records a SHA-256 per file so the evidence trail can be verified
later without re-downloading.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .tref import CONTRIBUTOR_TYPES, TrefClient, TrefError, YEAR_DELAY

SEARCH_TYPES = ("contributions", "expenditures")

_stop_requested = False


def _handle_interrupt(signum, frame):
    """Finish the current year, then stop — rather than leaving a torn directory."""
    global _stop_requested
    if _stop_requested:
        print("\n[abort] second interrupt — exiting immediately", flush=True)
        sys.exit(130)
    _stop_requested = True
    print("\n[stop] interrupt received; finishing the current year then stopping."
          "\n       press Ctrl-C again to abort now.", flush=True)


def log(msg: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def parse_years(spec: str) -> list:
    """Accept '2019-2026', '2019,2021,2024', or a mix of both."""
    years = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            lo, hi = int(lo), int(hi)
            if lo > hi:
                raise ValueError(f"range {part!r} counts backwards")
            years.update(range(lo, hi + 1))
        else:
            years.add(int(part))
    if not years:
        raise ValueError("no years given")
    return sorted(years)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_rows(path: Path) -> int:
    """Data rows in a CSV, excluding the header. Counted on bytes, not parsed."""
    with open(path, "rb") as fh:
        lines = sum(1 for _ in fh)
    return max(lines - 1, 0)


class Backfill:
    def __init__(self, root: Path, delay: bool = True):
        self.root = root
        self.delay = delay

    def year_dir(self, search_type: str, year: int) -> Path:
        return self.root / search_type / str(year)

    def is_done(self, search_type: str, year: int) -> bool:
        return (self.year_dir(search_type, year) / "_manifest.json").exists()

    def _fetch_partitioned(self, client, search_type: str, year: int, partial) -> None:
        """Fetch a year as four contributor-type searches, checkpointing each.

        TREF's paging cursor is server-side session state and cannot be resumed, so
        any failure discards the whole search. For a long year that is brutal: 2023
        lost 532 successfully downloaded batches because batch 533 ended prematurely.

        The four contributor types partition the result set exactly — every
        contribution comes from precisely one of them — so fetching each separately
        gives four shorter sessions AND four checkpoints. A completed partition is
        marked done and skipped on rerun, so a failure costs at most one partition
        instead of the year.
        """
        partial.mkdir(parents=True, exist_ok=True)
        for ctype in CONTRIBUTOR_TYPES:
            marker = partial / f"_{ctype}.done"
            if marker.exists():
                log(f"    {ctype}: already complete, skipping")
                continue
            # Clear any half-finished files from this partition's last attempt.
            stale = list(partial.glob(f"tn_{search_type}_{year}-{ctype[4:].lower()}-*.csv"))
            for f in stale:
                f.unlink()
            if stale:
                log(f"    {ctype}: cleared {len(stale)} file(s) from a previous attempt")
            log(f"    {ctype}: fetching ...")
            client.fetch_year(search_type, year, only_from=ctype)
            n = len(list(partial.glob(f"tn_{search_type}_{year}-{ctype[4:].lower()}-*.csv")))
            marker.write_text(json.dumps({"batches": n,
                                          "completed_at": datetime.now(timezone.utc).isoformat()}))
            log(f"    {ctype}: done, {n} batches checkpointed")

    def run_year(self, search_type: str, year: int, partitioned: bool = False) -> dict:
        final = self.year_dir(search_type, year)
        partial = final.with_name(f"{year}.partial")

        if partial.exists() and not partitioned:
            log(f"  discarding incomplete {partial.name} (cursor cannot be resumed)")
            shutil.rmtree(partial)

        started = time.time()
        client = TrefClient(out_dir=partial, delay=self.delay)

        if partitioned:
            self._fetch_partitioned(client, search_type, year, partial)
        else:
            client.fetch_year(search_type, year)

        files = sorted(partial.glob("*.csv"))
        rows = sum(count_rows(p) for p in files)
        manifest = {
            "search_type": search_type,
            "year": year,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.time() - started, 1),
            "batches": len(files),
            "data_rows": rows,
            "bytes": sum(p.stat().st_size for p in files),
            "source_url": "https://apps.tn.gov/tncamp/public/cesearch.htm",
            "files": [
                {"name": p.name, "bytes": p.stat().st_size,
                 "rows": count_rows(p), "sha256": sha256(p)}
                for p in files
            ],
        }
        (partial / "_manifest.json").write_text(json.dumps(manifest, indent=2))

        # Atomic promotion: the directory only becomes evidence once complete.
        final.parent.mkdir(parents=True, exist_ok=True)
        partial.rename(final)
        return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", required=True,
                        help="e.g. 2019-2026 or 2019,2021,2024")
    parser.add_argument("--types", default=",".join(SEARCH_TYPES),
                        help=f"comma-separated, from {SEARCH_TYPES}")
    parser.add_argument("--out", type=Path, default=None,
                        help="output root (default data/raw/tref/backfill)")
    parser.add_argument("--dry-run", action="store_true",
                        help="show what would be fetched, then exit")
    parser.add_argument("--no-delay", action="store_true",
                        help="skip polite delays — testing only, do not use on a real run")
    parser.add_argument("--partitioned", action="store_true",
                        help="fetch each year as four contributor-type searches, "
                             "checkpointing each. Use for years too long to finish in "
                             "one session — a failure then costs one partition, not the year")
    parser.add_argument("--force", action="store_true",
                        help="re-fetch years already marked complete")
    args = parser.parse_args(argv)

    try:
        years = parse_years(args.years)
    except ValueError as exc:
        parser.error(str(exc))

    types = [t.strip() for t in args.types.split(",") if t.strip()]
    bad = [t for t in types if t not in SEARCH_TYPES]
    if bad:
        parser.error(f"unknown type(s) {bad}; choose from {list(SEARCH_TYPES)}")

    root = args.out or (config.RAW_DIR / "tref" / "backfill")
    bf = Backfill(root, delay=not args.no_delay)

    jobs = [(t, y) for t in types for y in years]
    todo = jobs if args.force else [(t, y) for t, y in jobs if not bf.is_done(t, y)]
    done = len(jobs) - len(todo)

    log(f"backfill root : {root}")
    log(f"years         : {years[0]}-{years[-1]} ({len(years)})")
    log(f"types         : {', '.join(types)}")
    log(f"already done  : {done}")
    log(f"to fetch      : {len(todo)}")

    if args.dry_run:
        for t, y in todo:
            print(f"  would fetch {t} {y}")
        return 0

    if not todo:
        log("nothing to do — every requested year is already complete")
        return 0

    signal.signal(signal.SIGINT, _handle_interrupt)
    signal.signal(signal.SIGTERM, _handle_interrupt)

    totals = {"rows": 0, "bytes": 0, "batches": 0, "years": 0}
    failures = []

    for i, (search_type, year) in enumerate(todo, 1):
        if _stop_requested:
            log("stopping as requested; remaining years left untouched")
            break

        log(f"({i}/{len(todo)}) {search_type} {year} ...")
        try:
            m = bf.run_year(search_type, year, partitioned=args.partitioned)
        except TrefError as exc:
            # One bad year must not abandon the rest of an overnight run.
            log(f"  FAILED {search_type} {year}: {exc}")
            failures.append((search_type, year, str(exc)))
            continue
        except Exception as exc:  # noqa: BLE001 - unattended run, keep going
            log(f"  FAILED {search_type} {year}: {type(exc).__name__}: {exc}")
            failures.append((search_type, year, f"{type(exc).__name__}: {exc}"))
            continue

        log(f"  done: {m['data_rows']:,} rows in {m['batches']} batches, "
            f"{m['bytes']/1e6:.1f} MB, {m['elapsed_seconds']:.0f}s")
        totals["rows"] += m["data_rows"]
        totals["bytes"] += m["bytes"]
        totals["batches"] += m["batches"]
        totals["years"] += 1

        if i < len(todo) and not _stop_requested:
            time.sleep(__import__("random").uniform(*YEAR_DELAY))

    log("=" * 60)
    log(f"completed {totals['years']} year(s): {totals['rows']:,} rows, "
        f"{totals['batches']} batches, {totals['bytes']/1e6:.1f} MB")
    if failures:
        log(f"{len(failures)} failure(s) — rerun the same command to retry them:")
        for t, y, err in failures:
            log(f"  {t} {y}: {err[:100]}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
