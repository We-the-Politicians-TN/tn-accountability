"""Apply SQL migrations in filename order.

Usage:
    python -m tn_accountability.migrate          # apply pending migrations
    python -m tn_accountability.migrate --status # show what is applied

Each file in sql/migrations/ runs once, inside its own transaction, and is
recorded in `schema_migrations`. Files are never edited after being applied —
write a new numbered migration instead.
"""

from __future__ import annotations

import argparse
import hashlib
import sys

import psycopg

from . import config

MIGRATIONS_DIR = config.PROJECT_ROOT / "sql" / "migrations"

TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    text PRIMARY KEY,
    sha256      text NOT NULL,
    applied_at  timestamptz NOT NULL DEFAULT now()
)
"""


def migration_files() -> list:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def applied(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT filename, sha256 FROM schema_migrations")
        return dict(cur.fetchall())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true", help="show state and exit")
    args = parser.parse_args()

    with psycopg.connect(config.require("DATABASE_URL")) as conn:
        with conn.cursor() as cur:
            cur.execute(TRACKING_TABLE)
        conn.commit()

        already = applied(conn)

        for path in migration_files():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()

            if path.name in already:
                if already[path.name] != digest:
                    print(
                        f"CHANGED  {path.name} — already applied but the file has been "
                        f"edited since. Write a new migration instead of editing this one.",
                        file=sys.stderr,
                    )
                    return 1
                print(f"applied  {path.name}")
                continue

            if args.status:
                print(f"PENDING  {path.name}")
                continue

            print(f"applying {path.name} ...", end=" ", flush=True)
            try:
                with conn.cursor() as cur:
                    cur.execute(path.read_text())
                    cur.execute(
                        "INSERT INTO schema_migrations (filename, sha256) VALUES (%s, %s)",
                        (path.name, digest),
                    )
                conn.commit()
            except psycopg.Error as exc:
                conn.rollback()
                print("FAILED")
                print(f"\n{exc}", file=sys.stderr)
                return 1
            print("ok")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
