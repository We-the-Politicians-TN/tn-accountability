"""Load iLobby registrations and SS-8011 reports; apply employer subjects to donors.

    python -m tn_accountability.tec_lobby_load load
    python -m tn_accountability.tec_lobby_load classify

Reads what tec_lobby.fetch has saved so far (skip-if-loaded on report_id), so it can
run while the fetch is still going and again afterwards.

`classify` upgrades donor_category_map: any donor whose name keys to a registered
employer takes that employer's declared industry with confidence 95 and
assigned_by='ss8011' — authoritative, replacing the name-pattern guess. Human-reviewed
rows are never overwritten.
"""

from __future__ import annotations

import argparse
import json
import re

import psycopg

from . import config
from .legiscan import log
from .tec_soi import _clean

RAW = config.RAW_DIR / "tec" / "lobby"


def key(s: str) -> str:
    return re.sub(r'[^A-Z0-9]', '', (s or '').upper())


def parse_report(html: str) -> dict:
    t = _clean(html)
    def grab(a, b):
        i = t.find(a)
        if i < 0: return None
        j = t.find(b, i + len(a)) if b else -1
        return t[i + len(a): j if j > 0 else i + len(a) + 200].strip(' :-')
    nature = grab('Nature of Company Business', 'Nature / interest')
    subjects = [x.strip().lower() for x in re.split(r'\s+-\s+', nature or '') if x.strip()] if nature else []
    return dict(
        employer_name_raw=grab('Contact Information Name', 'Address'),
        ceo_raw=grab('Name of CEO', 'Name of CFO'), cfo_raw=grab('Name of CFO', 'Name of Lobbyist Supervisor'),
        nature_of_business_raw=nature, subjects=subjects,
        compensation_range_raw=grab('Total Aggregate Lobbyist Compensation Total', 'Lobbying-Related Expenses'),
        expenses_range_raw=grab('Lobbying-Related Expenses Total', 'Aggregate Total of All In-State Events'),
        in_state_events_raw=grab('Aggregate Total of All In-State Events Total', 'Lobbyist Information'),
    )


def parse_dashboard(html: str) -> list:
    """Lobbyists registered to this employer: (name, address, registration date, year)."""
    out = []
    year = None
    for chunk in re.split(r'<h3[^>]*>', html):
        m = re.match(r'\s*(20\d{2})', _clean(chunk))
        if m: year = int(m.group(1))
        for row in re.findall(r'<tr[^>]*>(.*?)</tr>', chunk, flags=re.S):
            cells = [_clean(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', row, flags=re.S)]
            lid = re.search(r'viewLobbyistDashboard\.htm\?lobbyistId=(\d+)', row)
            if cells and lid:
                address = cells[1] if len(cells) > 1 else None
                registered = cells[2] if len(cells) > 2 else None
                # Some year blocks put the registration date inside the address cell.
                if registered is None and address:
                    dm = re.search(r'(\d{4}-\d{2}-\d{2})\s*$', address)
                    if dm:
                        registered, address = dm.group(1), address[:dm.start()].strip()
                ym = re.match(r'(\d{4})', registered or '')
                out.append(dict(name=cells[0], address=address, registered=registered,
                                year=int(ym.group(1)) if ym else year, lobbyist_id=int(lid.group(1))))
    return out


def load(conn) -> None:
    n_emp = n_lob = n_rep = 0
    for man_path in sorted(RAW.glob("*/_manifest.json")):
        man = json.loads(man_path.read_text()); year = man["year"]; d = man_path.parent
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO data_pulls (source, search_type, data_year, source_files, notes)
                           VALUES ('tn_ethics_commission','ss8011',%s,%s,%s) RETURNING id""",
                        (year, [str(man_path.relative_to(config.PROJECT_ROOT))], f"iLobby {year}: {len(man['employers'])} employers"))
            pull = cur.fetchone()[0]
            for e in man["employers"]:
                cur.execute("""INSERT INTO lobbyist_employers (employer_name_raw, employer_name, registration_years, city, state,
                                 ilobby_employer_id, source_file, data_pull_id)
                               VALUES (%s,%s,ARRAY[%s]::smallint[],%s,%s,%s,%s,%s)
                               ON CONFLICT (ilobby_employer_id) DO UPDATE SET
                                 registration_years = (SELECT array_agg(DISTINCT y) FROM unnest(lobbyist_employers.registration_years || EXCLUDED.registration_years) y)
                               RETURNING id""",
                            (e["name"], ' '.join(e["name"].split()).upper(), year, e.get("city"), e.get("state"),
                             e["employer_id"], f"data/raw/tec/lobby/{year}/employers.html", pull))
                emp_id = cur.fetchone()[0]; n_emp += 1
                dash = d / "dashboards" / e.get("dashboard", "")
                if dash.exists():
                    for lb in parse_dashboard(dash.read_text()):
                        cur.execute("""INSERT INTO lobbyists (lobbyist_name_raw, lobbyist_name, lobbyist_employer_id,
                                         registration_years, ilobby_lobbyist_id, source_file, data_pull_id)
                                       SELECT %s,%s,%s,ARRAY[%s]::smallint[],%s,%s,%s
                                       WHERE NOT EXISTS (SELECT 1 FROM lobbyists WHERE ilobby_lobbyist_id=%s AND lobbyist_employer_id=%s)""",
                                    (lb["name"], ' '.join(lb["name"].split()).upper(), emp_id, lb["year"] or year,
                                     lb["lobbyist_id"], f"data/raw/tec/lobby/{year}/dashboards/{dash.name}", pull,
                                     lb["lobbyist_id"], emp_id))
                        n_lob += cur.rowcount
                for r in e.get("reports", []):
                    f = d / "reports" / r["file"]
                    if not f.exists(): continue
                    p = parse_report(f.read_text())
                    ym = re.search(r'(20\d{2})', r["label"] or '')
                    cur.execute("""INSERT INTO lobbying_reports (report_id, employer_id, lobbyist_employer_id, period_label,
                                     report_year, employer_name_raw, nature_of_business_raw, subjects, compensation_range_raw,
                                     expenses_range_raw, in_state_events_raw, ceo_raw, cfo_raw, source_file, sha256, data_pull_id)
                                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                   ON CONFLICT (report_id) DO NOTHING""",
                                (r["report_id"], e["employer_id"], emp_id, r["label"], int(ym.group(1)) if ym else year,
                                 p["employer_name_raw"], p["nature_of_business_raw"], p["subjects"], p["compensation_range_raw"],
                                 p["expenses_range_raw"], p["in_state_events_raw"], p["ceo_raw"], p["cfo_raw"],
                                 f"data/raw/tec/lobby/{year}/reports/{f.name}", r["sha256"], pull))
                    n_rep += cur.rowcount
            # Employer industry: first mapped non-'other' subject across its reports.
            cur.execute("""UPDATE lobbyist_employers le SET issue_areas = s.subjects, industry_category = s.cat
                           FROM (SELECT lr.lobbyist_employer_id,
                                        (array_agg(DISTINCT sub))[1:20] AS subjects,
                                        coalesce((SELECT m.category FROM unnest(array_agg(sub)) u(sub)
                                                  JOIN lobby_subject_category_map m ON m.subject=u.sub
                                                  WHERE m.category<>'other' LIMIT 1), 'other') AS cat
                                 FROM lobbying_reports lr, unnest(lr.subjects) sub GROUP BY 1) s
                           WHERE s.lobbyist_employer_id = le.id""")
            cur.execute("UPDATE data_pulls SET status='success', finished_at=now(), rows_added=%s WHERE id=%s", (n_emp+n_lob+n_rep, pull))
        conn.commit()
    log(f"employers {n_emp}, lobbyists {n_lob}, reports {n_rep}")


def classify(conn) -> None:
    """Donors that are registered employers take the employer's declared industry."""
    with conn.cursor() as cur:
        cur.execute("""
            WITH emp AS (SELECT regexp_replace(employer_name,'[^A-Z0-9]','','g') AS k, industry_category, id
                         FROM lobbyist_employers WHERE industry_category IS NOT NULL AND industry_category<>'other'),
                 don AS (SELECT DISTINCT donor_name, regexp_replace(donor_name,'[^A-Z0-9]','','g') AS k
                         FROM contributions WHERE recipient_legislator_id IS NOT NULL AND donor_name IS NOT NULL)
            INSERT INTO donor_category_map (donor_name, category, confidence, assigned_by, notes)
            SELECT d.donor_name, e.industry_category, 95, 'ss8011', 'registered employer of lobbyists #'||e.id
            FROM don d JOIN emp e ON e.k = d.k
            ON CONFLICT (donor_name) DO UPDATE SET category=EXCLUDED.category, confidence=95,
                 assigned_by='ss8011', notes=EXCLUDED.notes
            WHERE NOT donor_category_map.reviewed""")
        n = cur.rowcount
        cur.execute("""UPDATE donors dd SET lobbyist_employer_id = le.id, industry_category = coalesce(dd.industry_category, le.industry_category)
                       FROM lobbyist_employers le
                       WHERE regexp_replace(dd.canonical_name,'[^A-Z0-9]','','g') = regexp_replace(le.employer_name,'[^A-Z0-9]','','g')""")
    conn.commit()
    log(f"donors classified from employer registrations: {n}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["load", "classify"])
    a = p.parse_args(argv)
    with psycopg.connect(config.require("DATABASE_URL")) as conn:
        (load if a.cmd == "load" else classify)(conn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
