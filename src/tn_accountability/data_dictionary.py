"""Generate the data dictionary from the live database.

    python -m tn_accountability.data_dictionary

Written from the database rather than by hand, so it cannot drift out of step with
the schema. Column notes come from the COMMENT statements in the migrations, which
means the explanation of *why* a column exists lives next to its definition and is
published automatically.
"""

from __future__ import annotations

import datetime as dt

import psycopg

from . import config
from .legiscan import log

HEADER = """\
# Data dictionary

Generated from the live database on {today}. Do not edit by hand — run
`python -m tn_accountability.data_dictionary` instead.

This exists so anyone can check our work: what we store, where it came from, and
which columns are the original source text as published versus our cleaned version.

## The rules that shape this schema

**Raw text is always kept.** Columns ending `_raw` hold exactly what the source
published. The matching column without the suffix holds our cleaned version. Where
they disagree, the `_raw` column is the evidence. Where a value could not be parsed —
a filing dated 29 February in a non-leap year, for example — the raw text is kept and
the cleaned column is left empty. We do not guess.

**Nothing enters without provenance.** Every financial record carries a
`data_pull_id` pointing at the ingest run that loaded it, plus the source file and
line it came from, so any figure can be traced to a downloaded file.

**Unapproved matches are never counted.** A campaign finance filer name is attributed
to a legislator only after a human confirms the match. Until then it counts for
no one — we would rather understate than misattribute.

---

"""


def main(argv=None) -> int:
    out = [HEADER.format(today=dt.date.today().isoformat())]
    with psycopg.connect(config.require("DATABASE_URL")) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.relname, obj_description(c.oid), c.reltuples::bigint
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='public' AND c.relkind='r'
                  AND c.relname <> 'schema_migrations'
                ORDER BY c.relname""")
            tables = cur.fetchall()

            for name, table_comment, approx in tables:
                cur.execute("SELECT count(*) FROM " + name)
                exact = cur.fetchone()[0]
                out.append(f"## `{name}`\n")
                out.append(f"*{exact:,} rows.*\n")
                if table_comment:
                    out.append(f"\n{table_comment}\n")
                out.append("\n| Column | Type | Null | Notes |\n|---|---|---|---|\n")
                cur.execute("""
                    SELECT a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull,
                           col_description(a.attrelid, a.attnum)
                    FROM pg_attribute a
                    WHERE a.attrelid = %s::regclass AND a.attnum > 0 AND NOT a.attisdropped
                    ORDER BY a.attnum""", (name,))
                for col, typ, notnull, comment in cur.fetchall():
                    note = (comment or "").replace("\n", " ")
                    if col.endswith("_raw") and not note:
                        note = "Source text exactly as published."
                    out.append(f"| `{col}` | {typ} | {'no' if notnull else 'yes'} | {note} |\n")
                out.append("\n")

            # Functions carry the analysis logic, so they belong here too.
            out.append("---\n\n## Analysis functions and views\n\n")
            cur.execute("""
                SELECT p.proname, obj_description(p.oid)
                FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                WHERE n.nspname='public' AND p.proname LIKE 'f\\_%'
                ORDER BY p.proname""")
            for fn, comment in cur.fetchall():
                out.append(f"### `{fn}()`\n\n{comment or '_No description recorded._'}\n\n")
            cur.execute("""
                SELECT c.relname, obj_description(c.oid)
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='public' AND c.relkind='v' ORDER BY c.relname""")
            for v, comment in cur.fetchall():
                out.append(f"### `{v}` (view)\n\n{comment or '_No description recorded._'}\n\n")

            cur.execute("SELECT name, value, unit, description FROM review_thresholds ORDER BY name")
            out.append("---\n\n## Thresholds currently in force\n\n")
            out.append("| Setting | Value | What it does |\n|---|---|---|\n")
            for n_, v, u, desc in cur.fetchall():
                out.append(f"| `{n_}` | {v} {u or ''} | {desc} |\n")

    path = config.PROJECT_ROOT / "docs" / "data_dictionary.md"
    path.write_text("".join(out))
    log(f"wrote {path} ({len(tables)} tables)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
