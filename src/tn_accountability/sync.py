"""Scheduled incremental ingest. Run by GitHub Actions; safe to run by hand.

    python -m tn_accountability.sync tref       --expect-rows
    python -m tn_accountability.sync legiscan

Each run fetches, loads, and then reports what actually changed. It exits non-zero
when something went wrong, because a non-zero exit is what makes GitHub notify the
repository owner — a job that fails quietly is worse than no job at all.

**Zero rows is treated as a failure when rows were expected.** A scraper that silently
returns nothing looks identical to a quiet week, and the difference matters: this data
backs public claims about named officials. `--expect-rows` is set on the schedules that
run around filing deadlines.

TREF has no "changed since" filter — its search is year-granular — so the forward job
re-fetches the current year and reloads that slice with --replace. LegiScan does
support change detection, and `legiscan.fetch_dataset` already skips any session whose
`dataset_hash` is unchanged, so the daily job is cheap: one API call when nothing moved.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys

import psycopg

from . import config
from .legiscan import log


def table_counts(conn) -> dict:
    out = {}
    with conn.cursor() as cur:
        for t in ("contributions", "expenditures", "bills", "sponsorships",
                  "roll_calls", "votes", "legislators"):
            cur.execute(f"SELECT count(*) FROM {t}")
            out[t] = cur.fetchone()[0]
    return out


def run(module: str, *args) -> int:
    """Run one of our CLIs as a subprocess so a crash cannot poison this process."""
    cmd = [sys.executable, "-m", f"tn_accountability.{module}", *args]
    log(f"$ {' '.join(cmd[2:])}")
    env = dict(os.environ, PYTHONPATH="src")
    p = subprocess.run(cmd, env=env)
    return p.returncode


def summary(lines: list) -> None:
    """Write to the GitHub Actions run summary when present, always to stdout."""
    text = "\n".join(lines)
    print(text)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as fh:
            fh.write(text + "\n")


def sync_tref(conn, expect_rows: bool) -> int:
    year = dt.date.today().year
    log(f"TREF forward ingest for {year}")

    if run("backfill", "--years", str(year), "--force") != 0:
        summary([f"### TREF sync FAILED", f"Download of {year} did not complete."])
        return 1

    before = table_counts(conn)
    if run("load_tref", "--years", str(year), "--replace") != 0:
        summary(["### TREF sync FAILED", "Load step failed after a successful download."])
        return 1
    after = table_counts(conn)

    added_c = after["contributions"] - before["contributions"]
    added_e = after["expenditures"] - before["expenditures"]
    lines = [f"### TREF sync {year}",
             f"- contributions: {before['contributions']:,} -> {after['contributions']:,} ({added_c:+,})",
             f"- expenditures:  {before['expenditures']:,} -> {after['expenditures']:,} ({added_e:+,})"]

    # Re-matching is cheap and new filers appear constantly; without it a newly
    # elected member's money stays unlinked until someone notices.
    run("match_tref", "propose")
    run("match_tref", "link")
    run("classify", "donors")

    if expect_rows and added_c == 0 and added_e == 0:
        lines.append("")
        lines.append("**FAILED: zero rows added when rows were expected.**")
        lines.append("Either TREF published nothing, or the scraper broke. "
                     "See docs/scraper_health.md.")
        summary(lines)
        return 1

    summary(lines)
    return 0


def sync_legiscan(conn, expect_rows: bool) -> int:
    log("LegiScan incremental sync")
    before = table_counts(conn)

    # fetch_dataset compares dataset_hash and skips unchanged sessions, so a quiet
    # day costs a single getDatasetList call.
    if run("legiscan", "fetch", "--from-year", "2019") != 0:
        summary(["### LegiScan sync FAILED", "Dataset fetch failed."])
        return 1
    if run("load_legiscan") != 0:
        summary(["### LegiScan sync FAILED", "Load failed after a successful fetch."])
        return 1

    after = table_counts(conn)
    lines = ["### LegiScan sync"]
    for k in ("bills", "sponsorships", "roll_calls", "votes", "legislators"):
        d = after[k] - before[k]
        lines.append(f"- {k}: {before[k]:,} -> {after[k]:,} ({d:+,})")

    run("classify", "subjects")

    if expect_rows and all(after[k] == before[k] for k in ("bills", "votes")):
        lines.append("")
        lines.append("**FAILED: no bills or votes changed when change was expected.**")
        summary(lines)
        return 1

    summary(lines)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("source", choices=["tref", "legiscan"])
    p.add_argument("--expect-rows", action="store_true",
                   help="treat 'nothing changed' as a failure (use around filing deadlines)")
    args = p.parse_args(argv)

    with psycopg.connect(config.require("DATABASE_URL")) as conn:
        conn.autocommit = True
        if args.source == "tref":
            return sync_tref(conn, args.expect_rows)
        return sync_legiscan(conn, args.expect_rows)


if __name__ == "__main__":
    raise SystemExit(main())
