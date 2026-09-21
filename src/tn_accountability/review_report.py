"""Draft a neutral summary of one review-queue pattern, with its supporting records.

    python -m tn_accountability.review_report --list
    python -m tn_accountability.review_report --legislator 123 --industry healthcare

Produces a document that could be attached to a Registry of Election Finance or
Ethics Commission submission: every contribution and every bill listed with its date
and its source, so a reader can check each line against the original filing.

**This is a description of records, not an allegation.** It states what was filed and
when, cites the provisions a reader may wish to consult, and stops there. Determining
whether anything was improper is for the Registry, the Commission and the courts. The
language rules in language.py apply to the output and are checked before it is written.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import psycopg

from . import config
from .language import check_text
from .legiscan import log

TEMPLATE = """\
# Record summary: {legislator} — {industry_label}

Prepared {today} from public records. **This document makes no allegation.** It sets
out contributions and legislative activity as filed, so each line can be checked
against its original source.

## Subject

| | |
|---|---|
| Legislator | {legislator} |
| Party | {party} |
| Chamber and district | {chamber}, District {district} |
| Industry | {industry_label} |

## Pattern described

{legislator} received **{matched_total}** from **{matched_donors} donors** categorised
as {industry_label}, in the {lookback} days before introducing **{bill_count} bills**
concerning {industry_label}, introduced between {first_introduced} and {last_introduced}.

Over the same period {legislator} reported **{member_raised}** in total contributions,
against a median of **{chamber_median}** for the {chamber} — a ratio of
**{ratio}×**.

## Important context, which cuts against reading too much into this

- **Tennessee bars contributions while the General Assembly is in session.** Nearly
  every member therefore raises money in the same months, and nearly every bill has
  contributions behind it in the preceding weeks. Timing alone distinguishes no one,
  and is not the basis of this summary.
- **Industry donors giving to members who work on their industry is ordinary and
  lawful.** Members seek support from those affected by their work; those affected
  support members who engage with their concerns.
- **Donor industry is assigned by our own classification**, from donor names and
  registrations. It may be wrong in individual cases. Each donor is listed below so
  any misclassification is visible.
- A member's fundraising exceeding their chamber median is common and expected for
  leadership and competitive districts.

## Bills concerned

{bill_table}

## Contributions counted

{contribution_table}

Each contribution above falls within {lookback} days before at least one of the bills
listed. Each is counted once, even where several bills share an overlapping window.

## Sources

- Campaign finance: Tennessee Registry of Election Finance, apps.tn.gov/tncamp
- Bills, sponsorships and votes: LegiScan, used under CC BY 4.0
- Method and code: https://github.com/We-the-Politicians-TN/tn-accountability

## Provisions a reader may wish to consult

Tennessee Code Annotated Titles 2 (elections and campaign finance), 3 (the General
Assembly) and 8 (public officers), together with the House and Senate ethics codes.

Complaints may be submitted by any member of the public to the
[Registry of Election Finance](https://www.tn.gov/tref.html) or the
[Tennessee Ethics Commission](https://www.tn.gov/ethics.html).

## If this is wrong

We want to correct errors, including at the request of the legislator or their staff:
https://github.com/We-the-Politicians-TN/tn-accountability/issues
"""


def money(v) -> str:
    return f"${float(v or 0):,.2f}"


def fetch(conn, legislator_id: int, industry: str):
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout='900s'")
        cur.execute("""SELECT * FROM f_review_queue_grouped()
                       WHERE legislator_id=%s AND industry=%s""", (legislator_id, industry))
        cols = [c[0] for c in cur.description]
        row = cur.fetchone()
        if not row:
            return None, None, None, None
        pattern = dict(zip(cols, row))

        cur.execute("SELECT value FROM review_thresholds WHERE name='lookback_days'")
        lookback = int(cur.fetchone()[0])

        cur.execute("""SELECT b.bill_number, b.introduced_date, b.title, b.status,
                              b.legiscan_url, b.state_url
                       FROM sponsorships s JOIN bills b ON b.id=s.bill_id
                       JOIN LATERAL unnest(b.subjects) AS sub(subject) ON true
                       JOIN subject_category_map scm ON scm.subject=sub.subject
                       WHERE s.legislator_id=%s AND s.sponsor_type='primary'
                         AND scm.category=%s AND b.general_assembly=114
                         AND NOT coalesce(b.is_ceremonial,false)
                       GROUP BY 1,2,3,4,5,6 ORDER BY 2, 1""", (legislator_id, industry))
        bills = cur.fetchall()

        # Every contribution that qualifies, each counted once.
        cur.execute("""
            WITH pairs AS (
              SELECT DISTINCT b.introduced_date
              FROM sponsorships s JOIN bills b ON b.id=s.bill_id
              JOIN LATERAL unnest(b.subjects) AS sub(subject) ON true
              JOIN subject_category_map scm ON scm.subject=sub.subject
              WHERE s.legislator_id=%s AND s.sponsor_type='primary'
                AND scm.category=%s AND b.general_assembly=114
                AND NOT coalesce(b.is_ceremonial,false) AND b.introduced_date IS NOT NULL)
            SELECT DISTINCT c.id, c.contribution_date, c.donor_name_raw, c.amount,
                   c.source_report, c.source_record_id
            FROM contributions c JOIN donor_category_map d ON d.donor_name=c.donor_name
            JOIN pairs p ON c.contribution_date >= p.introduced_date - (%s || ' days')::interval
                        AND c.contribution_date <  p.introduced_date
            WHERE c.recipient_legislator_id=%s AND d.category=%s
            ORDER BY 2, 3""", (legislator_id, industry, lookback, legislator_id, industry))
        contribs = cur.fetchall()
    return pattern, bills, contribs, lookback


def render(pattern, bills, contribs, lookback) -> str:
    labels = {"healthcare": "health care", "telecom_tech": "telecom and technology",
              "real_estate": "real estate", "alcohol_gaming": "alcohol, tobacco and gaming",
              "party_caucus": "party and caucus"}
    industry_label = labels.get(pattern["industry"], pattern["industry"].replace("_", " "))

    bt = ["| Bill | Introduced | Status | Title |", "|---|---|---|---|"]
    for num, intro, title, status, lurl, surl in bills:
        link = f"[{num}]({surl or lurl})" if (surl or lurl) else num
        bt.append(f"| {link} | {intro} | {status or ''} | {(title or '')[:90]} |")

    ct = ["| Date | Donor (as filed) | Amount | Report |", "|---|---|---|---|"]
    total = 0.0
    for _id, date, donor, amt, report, rec in contribs:
        total += float(amt or 0)
        ct.append(f"| {date} | {donor} | {money(amt)} | {report or ''} |")
    ct.append(f"| | **{len(contribs)} contributions** | **{money(total)}** | |")

    return TEMPLATE.format(
        legislator=pattern["legislator"], industry_label=industry_label,
        today=dt.date.today().isoformat(), party=pattern["party"] or "—",
        chamber=(pattern["chamber"] or "").capitalize(), district=pattern["district"] or "—",
        matched_total=money(pattern["matched_total"]), matched_donors=pattern["matched_donors"],
        lookback=lookback, bill_count=pattern["bill_count"],
        first_introduced=pattern["first_introduced"], last_introduced=pattern["last_introduced"],
        member_raised=money(pattern["member_raised"]), chamber_median=money(pattern["chamber_median"]),
        ratio=pattern["ratio_to_median"], bill_table="\n".join(bt),
        contribution_table="\n".join(ct))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--list", action="store_true", help="show the queue")
    p.add_argument("--legislator", type=int)
    p.add_argument("--industry")
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)

    with psycopg.connect(config.require("DATABASE_URL")) as conn:
        conn.autocommit = True
        if args.list or not (args.legislator and args.industry):
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout='900s'")
                cur.execute("""SELECT legislator_id, legislator, party, industry,
                                      matched_total, matched_donors, bill_count, ratio_to_median
                               FROM f_review_queue_grouped() LIMIT 25""")
                print(f"  {'ID':>5} {'LEGISLATOR':<22} {'P':<2} {'INDUSTRY':<13} {'MATCHED':>10} {'DNR':>4} {'BILLS':>6}")
                for r in cur.fetchall():
                    print(f"  {r[0]:>5} {r[1][:21]:<22} {r[2] or '?':<2} {r[3][:12]:<13} "
                          f"{r[4]:>10,.0f} {r[5]:>4} {r[6]:>6}")
            return 0

        pattern, bills, contribs, lookback = fetch(conn, args.legislator, args.industry)
        if not pattern:
            log("no such pattern in the queue")
            return 1
        doc = render(pattern, bills, contribs, lookback)

        problems = check_text(doc, "review report")
        if problems:
            log("REFUSING to write — language-rule violation:")
            for x in problems[:5]:
                log(f"  {x}")
            return 1

        out = args.out or (config.PROJECT_ROOT / "data" / "processed" /
                           f"review_{args.legislator}_{args.industry}.md")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc)
        log(f"wrote {out}  ({len(contribs)} contributions, {len(bills)} bills)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
