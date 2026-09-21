"""The monthly checks from PLAN.md, run automatically.

    python -m tn_accountability.healthcheck

PLAN.md ends with four checks to run every month. A checklist a person has to
remember gets skipped, and the failure mode is silent: stale data that still looks
fine. This runs them and exits non-zero when something needs attention, so it can be
scheduled and will speak up on its own.

It reports problems; it does not fix them. Several need human judgement — new filer
names to confirm, new donors to categorise — and quietly auto-applying those would
defeat the point of the approval step.
"""

from __future__ import annotations

import datetime as dt

import psycopg

from . import config
from .legiscan import log

OK, WARN, FAIL = "ok", "warn", "FAIL"


def check(conn) -> list:
    results = []
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout='900s'")

        # 1. Did the scheduled runs complete?
        cur.execute("""SELECT source::text, max(started_at), count(*) FILTER (WHERE status='failed')
                       FROM data_pulls GROUP BY 1 ORDER BY 1""")
        for source, last, failed in cur.fetchall():
            age = (dt.datetime.now(dt.timezone.utc) - last).days
            # TREF runs weekly, LegiScan daily in session and weekly otherwise.
            limit = 10 if source == "tref" else 10
            level = OK if age <= limit else (WARN if age <= limit * 3 else FAIL)
            results.append((level, f"{source}: last run {age} days ago"
                                   + (f", {failed} failed run(s) on record" if failed else "")))

        # 2. Is the most recent filing period represented?
        cur.execute("""SELECT max(contribution_date) FROM contributions""")
        last_c = cur.fetchone()[0]
        if last_c:
            age = (dt.date.today() - last_c).days
            # Contributions legitimately stop during session, so a long gap in
            # spring is expected rather than broken. See docs/filing_calendar.md.
            in_session = dt.date.today().month in (2, 3, 4)
            level = OK if age <= 45 or in_session else WARN
            results.append((level, f"most recent contribution is {age} days old"
                                   + (" (in-session lull, expected)" if in_session and age > 45 else "")))

        # 3. Anything new needing a human?
        cur.execute("SELECT count(*) FROM legislator_tref_ids WHERE NOT approved")
        pending = cur.fetchone()[0]
        results.append(((WARN if pending else OK),
                        f"{pending} campaign finance filer name(s) awaiting confirmation"
                        " — their money is counted for no one until reviewed"))

        cur.execute("""SELECT count(*), coalesce(sum(t.amt),0) FROM (
                         SELECT c.donor_name, sum(c.amount) AS amt FROM contributions c
                         LEFT JOIN donor_category_map m ON m.donor_name=c.donor_name
                         WHERE c.recipient_legislator_id IS NOT NULL AND m.category IS NULL
                           AND donor_class(c.donor_name) IN ('pac','business')
                         GROUP BY 1 HAVING sum(c.amount) >= 10000) t""")
        n, amt = cur.fetchone()
        results.append(((WARN if n else OK),
                        f"{n} uncategorised organisation donor(s) over $10,000 (${amt:,.0f} total)"))

        cur.execute("""SELECT count(*) FROM legislators l
                       WHERE NOT EXISTS (SELECT 1 FROM legislator_tref_ids t
                                         WHERE t.legislator_id=l.id AND t.approved)""")
        unlinked = cur.fetchone()[0]
        results.append(((WARN if unlinked > 60 else OK),
                        f"{unlinked} legislators have no confirmed campaign finance match"))

        # 4. Coverage gaps that would silently skew analysis.
        cur.execute("""SELECT g.y FROM generate_series(2019, extract(year from now())::int) g(y)
                       WHERE NOT EXISTS (SELECT 1 FROM data_pulls p WHERE p.source='tref'
                         AND p.search_type='contributions' AND p.data_year=g.y AND p.status='success')""")
        missing = [r[0] for r in cur.fetchall()]
        results.append(((FAIL if missing else OK),
                        f"contribution years missing: {missing}" if missing
                        else "all contribution years 2019-present are loaded"))

        # 5. The database must stay writable.
        cur.execute("SHOW default_transaction_read_only")
        ro = cur.fetchone()[0]
        results.append(((FAIL if ro == "on" else OK),
                        "database is READ-ONLY — the disk is probably full" if ro == "on"
                        else "database is writable"))

        cur.execute("SELECT pg_size_pretty(pg_database_size(current_database())), pg_database_size(current_database())")
        pretty, size = cur.fetchone()
        results.append(((WARN if size > 6 * 1024**3 else OK), f"database size {pretty} (8 GB plan)"))
    return results


def main(argv=None) -> int:
    with psycopg.connect(config.require("DATABASE_URL")) as conn:
        conn.autocommit = True
        results = check(conn)

    worst = OK
    for level, msg in results:
        print(f"  [{level:>4}] {msg}")
        if level == FAIL:
            worst = FAIL
        elif level == WARN and worst == OK:
            worst = WARN

    print()
    if worst == FAIL:
        log("something needs attention now")
        return 1
    if worst == WARN:
        log("nothing broken; some items are waiting on a human")
        return 0
    log("all checks clear")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
