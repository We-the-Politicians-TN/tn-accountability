"""Build the public static site.

    python -m tn_accountability.site_build            # build to site/dist
    python -m tn_accountability.site_build --serve    # build, then serve locally

Queries Postgres at build time and writes plain HTML. The browser never talks to the
database, so no credential reaches a visitor and the deny-all RLS posture stays intact
(D55). Output is static files, which is exactly what Cloudflare serves.

Every page is checked against the project's language rules before it is written, and
the build FAILS on a violation rather than publishing one (see language.py).

Governing principle 1: a page is produced for EVERY legislator, of either party, not
only for those with something notable. Selective coverage would forfeit the project's
defence against a charge of bias.
"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
from pathlib import Path

import psycopg
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import config
from .language import check_attribution, check_text
from .legiscan import log

# Comparisons are scoped to the current General Assembly so members are compared
# like for like. Using all-time totals makes long-serving members look like outliers
# purely from tenure: Johnny Garrett reads as 2.31x the median all-time but 0.96x —
# slightly BELOW it — when compared only on the current Assembly. See D88.
CURRENT_GA = 114
CURRENT_GA_FROM = "2025-01-01"

SITE = config.PROJECT_ROOT / "site"
DIST = SITE / "dist"
LOOKBACK = config.LOOKBACK_DAYS


# --- small chart helpers: inline SVG, no JavaScript, no chart library ---------

def bar_chart(points, width=640, height=180, fmt="${:,.0f}") -> str:
    """points: [(label, value), ...] -> inline SVG bar chart."""
    if not points:
        return '<p class="muted">No data.</p>'
    vmax = max(v for _, v in points) or 1
    n = len(points)
    bw = width / n
    bars = []
    for i, (label, v) in enumerate(points):
        h = (v / vmax) * (height - 34)
        x, y = i * bw, height - 22 - h
        bars.append(
            f'<rect x="{x + bw * 0.12:.1f}" y="{y:.1f}" width="{bw * 0.76:.1f}" '
            f'height="{max(h, 0.6):.1f}" class="bar"><title>{label}: '
            f'{fmt.format(v)}</title></rect>')
        if n <= 16 or i % max(1, n // 12) == 0:
            bars.append(f'<text x="{x + bw / 2:.1f}" y="{height - 7}" '
                        f'class="axis" text-anchor="middle">{label}</text>')
    return (f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" '
            f'aria-label="bar chart">{"".join(bars)}</svg>')


def money(v) -> str:
    return "$0" if not v else f"${float(v):,.0f}"


# --- data ---------------------------------------------------------------------

def fetch_all(conn) -> dict:
    d = {}
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout='900s'")

        cur.execute("""
            SELECT count(DISTINCT l.id),
                   (SELECT count(*) FROM contributions),
                   (SELECT count(*) FROM contributions WHERE recipient_legislator_id IS NOT NULL),
                   (SELECT coalesce(sum(amount),0) FROM contributions WHERE recipient_legislator_id IS NOT NULL),
                   (SELECT count(*) FROM bills),
                   (SELECT count(*) FROM bills WHERE NOT coalesce(is_ceremonial,false)),
                   (SELECT count(*) FROM votes),
                   (SELECT min(contribution_date) FROM contributions),
                   (SELECT max(contribution_date) FROM contributions)
            FROM legislators l""")
        r = cur.fetchone()
        d["stats"] = dict(legislators=r[0], contributions=r[1], linked=r[2],
                          linked_dollars=r[3], bills=r[4], substantive=r[5],
                          votes=r[6], first_date=r[7], last_date=r[8])

        # Chamber medians, scoped to the CURRENT Assembly and to members serving in
        # it. An all-time median would compare a member of ten years' standing with a
        # freshman and call the difference fundraising.
        cur.execute("""
            SELECT f.chamber::text,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY f.total_raised),
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY f.pac_share_pct),
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY f.top10_concentration_pct),
                   count(*)
            FROM f_legislator_finance_period(%s) f
            WHERE f.total_raised > 0 AND EXISTS (
                SELECT 1 FROM legislator_terms t
                WHERE t.legislator_id = f.legislator_id AND t.general_assembly = %s)
            GROUP BY 1""", (CURRENT_GA_FROM, CURRENT_GA))
        d["medians"] = {r[0]: dict(raised=r[1], pac=r[2], top10=r[3], n=r[4])
                        for r in cur.fetchall()}

        # Every legislator, both parties, whether or not they have money linked.
        cur.execute("""
            SELECT f.legislator_id, f.legislator, f.party, f.chamber::text, f.district,
                   f.total_raised, f.contribution_count, f.pac_share_pct,
                   f.top10_concentration_pct, f.total_spent,
                   (SELECT count(*) FROM sponsorships s JOIN bills b ON b.id=s.bill_id
                     WHERE s.legislator_id=f.legislator_id AND s.sponsor_type='primary'
                       AND NOT coalesce(b.is_ceremonial,false)) AS bills_primary,
                   (SELECT count(*) FROM legislator_terms t
                     WHERE t.legislator_id=f.legislator_id AND t.general_assembly=114) > 0 AS current
            FROM v_legislator_finance f
            ORDER BY f.total_raised DESC NULLS LAST""")
        cols = [c[0] for c in cur.description]
        d["legislators"] = [dict(zip(cols, r)) for r in cur.fetchall()]

        # Current-Assembly figures, used for every comparison and ratio.
        cur.execute("""SELECT legislator_id, total_raised, pac_share_pct,
                              top10_concentration_pct, contribution_count
                       FROM f_legislator_finance_period(%s)""", (CURRENT_GA_FROM,))
        d["current"] = {r[0]: dict(raised=r[1], pac=r[2], top10=r[3], n=r[4])
                        for r in cur.fetchall()}

        # Subject-matched results for the 114th, keyed by legislator.
        cur.execute("""
            SELECT legislator_id, bill_number, bill_title, introduced_date,
                   bill_categories, matched_total, all_pre_intro_total
            FROM f_subject_matched(%s, 114) WHERE sponsor_type='primary'
              AND matched_total > 0
            ORDER BY matched_total DESC""", (LOOKBACK,))
        matched = {}
        for r in cur.fetchall():
            matched.setdefault(r[0], []).append(dict(
                bill=r[1], title=r[2], introduced=r[3], cats=r[4] or [],
                matched=r[5], all_pre=r[6]))
        d["matched"] = matched

        # Per-legislator detail: quarterly money, top donors, top vendors.
        cur.execute("""
            SELECT recipient_legislator_id,
                   to_char(date_trunc('quarter', contribution_date), 'YYYY "Q"Q'),
                   sum(amount)
            FROM contributions WHERE recipient_legislator_id IS NOT NULL
              AND contribution_date IS NOT NULL
            GROUP BY 1,2 ORDER BY 1,2""")
        quarters = {}
        for lid, q, amt in cur.fetchall():
            quarters.setdefault(lid, []).append((q, float(amt or 0)))
        d["quarters"] = quarters

        cur.execute("""
            SELECT recipient_legislator_id, donor_name, sum(amount), count(*)
            FROM contributions WHERE recipient_legislator_id IS NOT NULL
              AND donor_name IS NOT NULL
            GROUP BY 1,2 ORDER BY 1, 3 DESC""")
        donors = {}
        for lid, name, amt, n in cur.fetchall():
            lst = donors.setdefault(lid, [])
            if len(lst) < 10:
                lst.append(dict(name=name, total=amt, n=n))
        d["donors"] = donors

        cur.execute("""
            SELECT spender_legislator_id, vendor_name, sum(amount), count(*)
            FROM expenditures WHERE spender_legislator_id IS NOT NULL
              AND vendor_name IS NOT NULL
            GROUP BY 1,2 ORDER BY 1, 3 DESC""")
        vendors = {}
        for lid, name, amt, n in cur.fetchall():
            lst = vendors.setdefault(lid, [])
            if len(lst) < 10:
                lst.append(dict(name=name, total=amt, n=n))
        d["vendors"] = vendors

        # The review queue, one row per (legislator, industry) so no contribution is
        # counted twice across bills with overlapping windows (D93).
        cur.execute("""SELECT legislator_id, legislator, party, chamber::text, district,
                              industry, bill_numbers, bill_count, first_introduced,
                              last_introduced, matched_total, matched_donors,
                              member_raised, chamber_median, ratio_to_median
                       FROM f_review_queue_grouped()""")
        cols = [c[0] for c in cur.description]
        d["queue"] = [dict(zip(cols, r)) for r in cur.fetchall()]

        cur.execute("SELECT name, value, unit, description FROM review_thresholds ORDER BY name")
        d["thresholds"] = [dict(name=r[0], value=r[1], unit=r[2], description=r[3])
                           for r in cur.fetchall()]

        # Coverage caveats, shown rather than hidden.
        cur.execute("SELECT count(*) FROM legislator_tref_ids WHERE NOT approved")
        d["pending_matches"] = cur.fetchone()[0]
        cur.execute("""SELECT coalesce(sum(c.amount) FILTER (WHERE m.category IS NOT NULL),0),
                              coalesce(sum(c.amount),0)
                       FROM contributions c
                       LEFT JOIN donor_category_map m ON m.donor_name=c.donor_name
                       WHERE c.recipient_legislator_id IS NOT NULL""")
        cat, tot = cur.fetchone()
        d["category_coverage"] = round(100.0 * float(cat) / float(tot), 1) if tot else 0
        cur.execute("""SELECT data_year FROM generate_series(2019, extract(year from now())::int) g(data_year)
                       WHERE NOT EXISTS (SELECT 1 FROM data_pulls p WHERE p.source='tref'
                          AND p.search_type='contributions' AND p.data_year=g.data_year
                          AND p.status='success')""")
        d["missing_years"] = [r[0] for r in cur.fetchall()]
    return d


def ratio(value, med):
    if not value or not med:
        return None
    return round(float(value) / float(med), 2)


def build(serve: bool = False) -> int:
    env = Environment(loader=FileSystemLoader(SITE / "templates"),
                      autoescape=select_autoescape(["html"]))
    env.filters["money"] = money

    with psycopg.connect(config.require("DATABASE_URL")) as conn:
        conn.autocommit = True
        log("querying...")
        d = fetch_all(conn)

    DIST.mkdir(parents=True, exist_ok=True)
    for p in DIST.iterdir():
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    shutil.copytree(SITE / "static", DIST / "static")

    built_at = dt.datetime.now(dt.timezone.utc)
    common = dict(stats=d["stats"], medians=d["medians"], built_at=built_at,
                  thresholds=d["thresholds"],
                  lookback=LOOKBACK, pending_matches=d["pending_matches"],
                  category_coverage=d["category_coverage"],
                  missing_years=d["missing_years"])

    # Attach baseline-relative figures. Everything is expressed against the member's
    # own chamber, because the chambers differ substantially (House median $258,832,
    # Senate $569,306) and comparing across them would mislead.
    for L in d["legislators"]:
        med = d["medians"].get(L["chamber"], {})
        cur_fin = d["current"].get(L["legislator_id"], {})
        # All-time stays on the member's own profile as their history; the RATIO is
        # computed on the current Assembly only, so the comparison is fair.
        L["current_raised"] = cur_fin.get("raised") or 0
        L["current_pac"] = cur_fin.get("pac")
        L["ratio"] = ratio(L["current_raised"], med.get("raised"))
        L["matched_bills"] = d["matched"].get(L["legislator_id"], [])
        L["matched_total"] = sum(float(m["matched"] or 0) for m in L["matched_bills"])

    pages = []
    pages.append(("index.html", env.get_template("index.html").render(
        legislators=d["legislators"], **common)))
    pages.append(("legislators.html", env.get_template("legislators.html").render(
        legislators=d["legislators"], **common)))
    pages.append(("methodology.html", env.get_template("methodology.html").render(**common)))

    pages.append(("patterns.html", env.get_template("patterns.html").render(
        queue=d["queue"], **common)))

    tpl = env.get_template("legislator.html")
    for L in d["legislators"]:
        lid = L["legislator_id"]
        pages.append((f"legislator/{lid}.html", tpl.render(
            L=L, quarters=d["quarters"].get(lid, []),
            donors=d["donors"].get(lid, []), vendors=d["vendors"].get(lid, []),
            chart=bar_chart(d["quarters"].get(lid, [])), **common)))

    # Enforce the language rules before anything is written.
    problems = []
    for name, html in pages:
        problems += check_text(html, name)
        problems += check_attribution(html, name)
    if problems:
        log(f"BUILD FAILED — {len(problems)} language-rule violation(s):")
        for p in problems[:15]:
            log(f"  {p}")
        return 1

    for name, html in pages:
        out = DIST / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html)
    log(f"built {len(pages)} pages -> {DIST}")

    if serve:
        import http.server, socketserver, os
        os.chdir(DIST)
        log("serving on http://localhost:8080 (ctrl-c to stop)")
        socketserver.TCPServer(("", 8080), http.server.SimpleHTTPRequestHandler).serve_forever()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--serve", action="store_true")
    return build(p.parse_args(argv).serve)


if __name__ == "__main__":
    raise SystemExit(main())
