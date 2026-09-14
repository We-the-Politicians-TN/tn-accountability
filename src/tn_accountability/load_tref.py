"""Load downloaded TREF CSVs into Postgres.

    python -m tn_accountability.load_tref --years 2019-2026
    python -m tn_accountability.load_tref --years 2024 --types contributions --replace

Works on whole (search_type, year) slices, because that is the unit the backfill
downloads and the unit TREF's own paging defines. A slice already loaded is
skipped unless --replace is given, which deletes that slice's rows first.

Rows are inserted with COPY, not INSERT — at ~2M rows the difference is hours.

Every row keeps the source file and its line number in `source_record_id`, so any
figure on the public site can be traced to an exact line of an exact downloaded
file, and that file's SHA-256 is recorded in the year's manifest.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import psycopg

from . import config
from .backfill import SEARCH_TYPES, log, parse_years

# TREF header -> our column. Anything not listed here is a schema gap, and the
# loader refuses to run rather than silently discarding a published field.
CONTRIB_MAP = {
    "Type": "transaction_type_raw",
    "Adj": "adjustment_raw",
    "Amount": "amount_raw",
    "Date": "contribution_date_raw",
    "Election Year": "election_year_raw",
    "Report Name": "source_report",
    "Recipient Name": "recipient_name_raw",
    "Contributor Name": "donor_name_raw",
    "Contributor Address": "donor_address_raw",
    "Contributor Occupation": "donor_occupation_raw",
    "Contributor Employer": "donor_employer_raw",
    "Description": "description_raw",
}
EXPEND_MAP = {
    "Type": "transaction_type_raw",
    "Adj": "adjustment_raw",
    "Amount": "amount_raw",
    "Date": "expenditure_date_raw",
    "Election Year": "election_year_raw",
    "Report Name": "source_report",
    "Candidate/PAC Name": "spender_name_raw",
    "Vendor Name": "vendor_name_raw",
    "Vendor Address": "vendor_address_raw",
    "Purpose": "purpose_raw",
    "Candidate For": "candidate_for_raw",
    "S/O": "support_oppose_raw",
}

_MONEY = re.compile(r"[^0-9.\-]")


def parse_amount(raw: str):
    """'$1,500.00' -> Decimal-safe string. Returns None if it cannot be read."""
    if not raw:
        return None
    cleaned = _MONEY.sub("", raw.replace("(", "-").replace(")", ""))
    if cleaned in ("", "-", "."):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_date(raw: str):
    if not raw:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def parse_year(raw: str):
    if not raw:
        return None
    m = re.search(r"(19|20)\d{2}", raw)
    return int(m.group(0)) if m else None


def parse_yn(raw: str):
    if not raw:
        return None
    v = raw.strip().upper()
    return True if v in ("Y", "YES", "TRUE") else False if v in ("N", "NO", "FALSE") else None


def normalize(text: str):
    """Collapse whitespace and uppercase, for matching. Raw text is kept separately."""
    if not text:
        return None
    return " ".join(text.split()).upper() or None


class Loader:
    def __init__(self, conn, root: Path):
        self.conn = conn
        self.root = root

    def slice_loaded(self, search_type: str, year: int) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT 1 FROM data_pulls
                   WHERE source='tref' AND search_type=%s AND data_year=%s
                     AND status='success' LIMIT 1""",
                (search_type, year))
            return cur.fetchone() is not None

    def delete_slice(self, search_type: str, year: int) -> int:
        table = "contributions" if search_type == "contributions" else "expenditures"
        with self.conn.cursor() as cur:
            cur.execute(
                f"""DELETE FROM {table} WHERE data_pull_id IN (
                        SELECT id FROM data_pulls
                        WHERE source='tref' AND search_type=%s AND data_year=%s)""",
                (search_type, year))
            deleted = cur.rowcount
            cur.execute(
                """DELETE FROM data_pulls
                   WHERE source='tref' AND search_type=%s AND data_year=%s""",
                (search_type, year))
        return deleted

    def load_slice(self, search_type: str, year: int) -> dict:
        year_dir = self.root / search_type / str(year)
        manifest_path = year_dir / "_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(
                f"{search_type} {year} is not downloaded (no manifest at {manifest_path})")
        manifest = json.loads(manifest_path.read_text())
        files = sorted(year_dir.glob("*.csv"))

        with self.conn.cursor() as cur:
            cur.execute(
                """INSERT INTO data_pulls (source, search_type, data_year, source_files, notes)
                   VALUES ('tref', %s, %s, %s, %s) RETURNING id""",
                (search_type, year,
                 [str(p.relative_to(config.PROJECT_ROOT)) for p in files],
                 f"backfill load of {len(files)} batch files"))
            pull_id = cur.fetchone()[0]

        table = "contributions" if search_type == "contributions" else "expenditures"
        colmap = CONTRIB_MAP if search_type == "contributions" else EXPEND_MAP
        rows = self._copy_files(table, colmap, files, pull_id, search_type)

        with self.conn.cursor() as cur:
            cur.execute(
                """UPDATE data_pulls SET status='success', finished_at=now(), rows_added=%s
                   WHERE id=%s""", (rows, pull_id))
        self.conn.commit()
        return {"rows": rows, "files": len(files), "pull_id": pull_id,
                "manifest_rows": manifest["data_rows"]}

    def _copy_files(self, table, colmap, files, pull_id, search_type) -> int:
        is_contrib = search_type == "contributions"
        date_col = "contribution_date" if is_contrib else "expenditure_date"
        name_raw = "donor_name_raw" if is_contrib else "vendor_name_raw"
        name_col = "donor_name" if is_contrib else "vendor_name"
        who_raw = "recipient_name_raw" if is_contrib else "spender_name_raw"
        who_col = "recipient_name" if is_contrib else "spender_name"

        target = list(colmap.values()) + [
            "amount", date_col, "election_year", "is_adjustment",
            "transaction_type", name_col, who_col,
            "source_file", "source_record_id", "data_pull_id",
        ]

        total = 0
        with self.conn.cursor() as cur:
            copy_sql = f"COPY {table} ({', '.join(target)}) FROM STDIN"
            with cur.copy(copy_sql) as cp:
                for path in files:
                    rel = str(path.relative_to(config.PROJECT_ROOT))
                    with open(path, encoding="latin-1", newline="") as fh:
                        reader = csv.DictReader(fh)
                        missing = set(colmap) - set(reader.fieldnames or [])
                        extra = set(reader.fieldnames or []) - set(colmap)
                        if missing or extra:
                            raise RuntimeError(
                                f"{rel}: TREF columns changed. missing={sorted(missing)} "
                                f"unmapped={sorted(extra)}. Refusing to load rather than "
                                f"silently dropping a published field.")
                        for lineno, row in enumerate(reader, start=2):
                            vals = [row.get(src) or None for src in colmap]
                            vals += [
                                parse_amount(row.get("Amount", "")),
                                parse_date(row.get("Date", "")),
                                parse_year(row.get("Election Year", "")),
                                parse_yn(row.get("Adj", "")),
                                normalize(row.get("Type", "")),
                                normalize(row.get(
                                    "Contributor Name" if is_contrib else "Vendor Name", "")),
                                normalize(row.get(
                                    "Recipient Name" if is_contrib else "Candidate/PAC Name", "")),
                                rel,
                                f"{path.name}:{lineno}",
                                pull_id,
                            ]
                            cp.write_row(vals)
                            total += 1
        return total


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", required=True)
    parser.add_argument("--types", default=",".join(SEARCH_TYPES))
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--replace", action="store_true",
                        help="reload slices already in the database")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    years = parse_years(args.years)
    types = [t.strip() for t in args.types.split(",") if t.strip()]
    root = args.root or (config.RAW_DIR / "tref" / "backfill")

    with psycopg.connect(config.require("DATABASE_URL")) as conn:
        loader = Loader(conn, root)
        planned, skipped = [], []
        for t in types:
            for y in years:
                if not (root / t / str(y) / "_manifest.json").exists():
                    continue
                (skipped if loader.slice_loaded(t, y) and not args.replace else planned).append((t, y))

        log(f"downloaded slices found : {len(planned) + len(skipped)}")
        log(f"already loaded (skipping): {len(skipped)}")
        log(f"to load                  : {len(planned)}")
        if args.dry_run:
            for t, y in planned:
                print(f"  would load {t} {y}")
            return 0

        grand = 0
        for t, y in planned:
            if args.replace:
                gone = loader.delete_slice(t, y)
                conn.commit()
                if gone:
                    log(f"  replaced: deleted {gone:,} existing {t} {y} rows")
            log(f"loading {t} {y} ...")
            r = loader.load_slice(t, y)
            flag = "" if r["rows"] == r["manifest_rows"] else \
                   f"  <- MISMATCH, manifest says {r['manifest_rows']:,}"
            log(f"  {r['rows']:,} rows from {r['files']} files{flag}")
            grand += r["rows"]
        log(f"total loaded: {grand:,} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
