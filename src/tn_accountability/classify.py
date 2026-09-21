"""Assign industry categories to donors and bill subjects.

    python -m tn_accountability.classify subjects   # map LegiScan subjects
    python -m tn_accountability.classify donors     # map donor entities
    python -m tn_accountability.classify review     # export top-200 donors for a human

Bill subjects and donor industries must land in the SAME vocabulary or they cannot
be matched, so both use `industry_categories`. Rules live here; the assignments they
produce live in tables, where a human can correct them and where the methodology page
can cite them.

Phase 5 showed contribution timing is a calendar artifact (D73), so this subject
match is the project's primary signal rather than a refinement of one.

Nothing here is authoritative. Rules propose; `reviewed` records a human agreeing.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import psycopg

from . import config
from .legiscan import log

# --- donor name -> industry --------------------------------------------------
# Ordered: the first pattern that matches wins, so put specific before general.
DONOR_RULES = [
    # Patterns are PREFIXES (leading \b only, no trailing \b). An earlier version
    # used \bBANK\b, which cannot match "BANKERS" — the trailing boundary requires
    # the word to end there. That silently dropped Tennessee Bankers Assn PAC,
    # Tennessee Realtors PAC, Lawyers Involved for TN and many more. Only short or
    # ambiguous tokens keep a trailing boundary.
    # HOSPITAL must not swallow HOSPITALITY, and NURS must not swallow NURSERY.
    # Both collisions were live: 14 donors and $184,500 of restaurant and hotel money
    # was counted as health care, including Tennessee Hospitality PAC and Ryman
    # Hospitality. Caught only by checking a generated report line by line against
    # its sources — which is why that check is not optional.
    ("healthcare",    r"\b(HOSPITAL(?!ITY)|HEALTH|MEDIC|PHYSICIAN|DOCTOR|SURGER|SURGIC|"
                      r"DENTAL|DENTIST|NURSING|NURSE\b|PHARMAC|HCA\b|TRISTAR|TENNCARE|"
                      r"CLINIC|THERAP|ORTHO|RADIOL|"
                      r"ONCOL|PEDIATR|ANESTH|CHIROPRAC|OPTOMETR|HOSPICE|\bTHA\b|"
                      r"INDEPENDENT MEDICINE|LONG.?TERM CARE|ASSISTED LIVING)"),
    ("insurance",     r"\b(INSURANC|INSURER|UNDERWRIT|ACTUAR|CASUALT|ALLSTATE|"
                      r"STATE FARM|BLUE ?CROSS|TITLE INS|LIFE UNDERWRIT)"),
    ("finance",       r"\b(BANK|CREDIT UNION|FINANCIAL|FINANCE|LENDING|LOAN|MORTGAG|"
                      r"INVEST|SECURITIES|PAYDAY|CASH ADVANCE|TITLE LOAN|ACCOUNTANT|"
                      r"\bCPA\b|ADVANCE FINANCIAL)"),
    ("real_estate",   r"\b(REALTOR|REAL ESTATE|APARTMENT|PROPERT|DEVELOPER|HOMEBUILD|"
                      r"HOME BUILD|LANDLORD|RESIDENTIAL|HOUSING|\bRPAC\b)"),
    ("construction",  r"\b(CONTRACTOR|CONSTRUCT|HIGHWAY|PAVING|ASPHALT|CONCRETE|"
                      r"ROOFING|PLUMB|ENGINEER|ARCHITECT|AGGREGATE|QUARRY|CEMENT|"
                      r"EXCAVAT|MASONRY)"),
    ("energy",        r"\b(ENERGY|ELECTRIC|POWER|PIPELINE|UTILIT|PETROL|PROPANE|"
                      r"SOLAR|NUCLEAR|\bTVA\b|ATMOS|VALERO|EXXON|CHEVRON|\bGAS\b|\bOIL\b)"),
    ("telecom_tech",  r"\b(TELECOM|WIRELESS|BROADBAND|CABLE|INTERNET|COMCAST|AT&T|"
                      r"VERIZON|T.?MOBILE|CHARTER COMM|SOFTWARE|TECHNOL|DATA CENT|"
                      r"MICROSOFT|GOOGLE|AMAZON|ORACLE|\bIBM\b|COMMUNICATIONS)"),
    ("education",     r"\b(EDUCAT|\bEDUC\b|SCHOOL|TEACHER|UNIVERSIT|COLLEG|ACADEM|"
                      r"CHARTER SCHOOL|STUDENT|\bTEA\b|\bTSSAA\b|LEARNING)"),
    ("legal",         r"\b(LAWYER|ATTORNEY|LEGAL|TRIAL|BAR ASSOC|LAW FIRM|LITIGAT|"
                      r"COUNSEL|JUSTICE)"),
    ("agriculture",   r"\b(FARM|AGRI|CATTLE|POULTRY|DAIRY|SOYBEAN|COTTON|FORESTR|"
                      r"TIMBER|LUMBER|GROWER|RANCH)"),
    ("transport",     r"\b(TRUCK|TRANSPORT|RAIL|AIRLINE|AVIAT|LOGISTIC|FREIGHT|"
                      r"AUTOMOBILE|AUTO DEALER|CAR DEALER|MOTOR|FEDEX|\bUPS\b|"
                      r"DELIVERY|SHIPPING|TOWING)"),
    ("hospitality",   r"\b(RESTAURANT|HOTEL|MOTEL|LODGING|HOSPITALIT|RETAIL|GROCER|"
                      r"BEVERAGE|CONVENIENCE|WALMART|KROGER|DOLLAR GENERAL)"),
    ("labor",         r"\b(UNION|LABOR|LABOUR|AFL.?CIO|TEAMSTER|\bUAW\b|\bIBEW\b|"
                      r"CARPENTER|PAINTER|PLUMBERS|FIREFIGHT|POLICE BENEV|\bCWA\b|"
                      r"\bCOPE\b|LOCAL \d+|EMPLOYEES)"),
    ("alcohol_gaming",r"\b(BEER|WINE|SPIRITS|LIQUOR|DISTILL|BREWER|ALCOHOL|TOBACCO|"
                      r"VAPE|VAPOR|CIGAR|NICOTINE|ALTRIA|REYNOLDS|LOTTER|GAMING|"
                      r"CASINO|WAGER)"),
    ("firearms",      r"\b(FIREARM|\bGUN\b|GUNS\b|RIFLE|AMMUNIT|SHOOTING|\bNRA\b|SPORTSMAN)"),
    ("manufacturing", r"\b(MANUFACTUR|INDUSTR|FACTORY|CHEMICAL|STEEL|PLASTIC|PAPER|"
                      r"TEXTILE|NISSAN|VOLKSWAGEN|GENERAL MOTORS|\bGM\b|\bFORD\b)"),
    ("party_caucus",  r"\b(REPUBLICAN|DEMOCRAT|CAUCUS|\bPARTY\b|\bGOP\b|\bDNC\b|\bRNC\b)"),
]

# --- LegiScan subject -> industry --------------------------------------------
SUBJECT_RULES = [
    ("healthcare",    r"HEALTH|MEDIC|HOSPITAL|TENNCARE|DRUG|PHARMAC|MENTAL|NURSING|"
                      r"PHYSICIAN|DENTIST|ABORTION|OPIOID|DISABILIT"),
    ("insurance",     r"INSURANCE|WORKERS.? COMP"),
    ("finance",       r"BANK|FINANCIAL|CREDIT|LOAN|SECURITIES|INVESTMENT|TAXATION|"
                      r"TAXES|REVENUE|BUDGET|APPROPRIAT"),
    ("real_estate",   r"REAL (PROPERTY|ESTATE)|HOUSING|LANDLORD|TENANT|ZONING|"
                      r"PROPERTY TAX|HOMEOWNER"),
    ("construction",  r"CONSTRUCTION|CONTRACTOR|BUILDING|INFRASTRUCTURE|PUBLIC WORKS"),
    ("energy",        r"ENERGY|ELECTRIC|UTILIT|GAS|PETROLEUM|SOLAR|NUCLEAR|WATER|"
                      r"ENVIRONMENT|CONSERVATION|MINING"),
    ("telecom_tech",  r"TELECOMMUNICAT|BROADBAND|INTERNET|TECHNOLOG|DATA|PRIVACY|"
                      r"ARTIFICIAL INTELLIGENCE|CYBER|SOCIAL MEDIA"),
    ("education",     r"EDUCATION|SCHOOL|TEACHER|STUDENT|UNIVERSIT|COLLEG|"
                      r"LOCAL EDUCATION|CHARTER|LIBRAR|TEXTBOOK"),
    ("legal",         r"COURT|JUDICIAL|JUDGE|ATTORNEY|CIVIL PROCEDURE|TORT|"
                      r"LIABILIT|EVIDENCE|CRIMINAL|CORRECTION|PRISON|SENTENC|"
                      r"JUVENILE|LAW ENFORCEMENT|SHERIFF"),
    ("agriculture",   r"AGRICULTUR|FARM|LIVESTOCK|FOREST|WILDLIFE|HUNTING|FISH"),
    ("transport",     r"TRANSPORT|HIGHWAY|ROAD|MOTOR VEHICLE|TRAFFIC|DRIVER|"
                      r"AVIATION|RAILROAD|TRUCK|BRIDGE"),
    ("hospitality",   r"RESTAURANT|HOTEL|TOURISM|FOOD|GROCERY|RETAIL|"
                      r"CONSUMER PROTECTION|SALES"),
    ("labor",         r"LABOR|EMPLOYMENT|WAGE|UNEMPLOYMENT|WORKPLACE|"
                      r"COLLECTIVE BARGAIN|PUBLIC EMPLOYEE|RETIREMENT SYSTEM"),
    ("alcohol_gaming",r"ALCOHOL|BEER|WINE|LIQUOR|TOBACCO|VAPOR|LOTTERY|GAMING|GAMBLING"),
    ("firearms",      r"FIREARM|WEAPON|AMMUNITION|HANDGUN"),
    ("manufacturing", r"MANUFACTUR|INDUSTRIAL|COMMERCE|BUSINESS|CORPORAT|ECONOMIC DEVELOP"),
    ("party_caucus",  r"ELECTION|CAMPAIGN|POLITICAL|VOTER|REDISTRICT|ETHICS|LOBBY"),
]


def first_match(text: str, rules) -> tuple:
    if not text:
        return None, 0
    up = text.upper()
    for cat, pattern in rules:
        if re.search(pattern, up):
            return cat, 75          # rule-based: useful, not authoritative
    return None, 0


def classify_subjects(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT s FROM bills, unnest(subjects) s")
        subjects = [r[0] for r in cur.fetchall()]
        rows, unmatched = [], 0
        for s in subjects:
            # Ceremonial subjects never carry policy content; never categorise them.
            if re.match(r"^MEMORIALS", s.upper()):
                continue
            cat, _ = first_match(s, SUBJECT_RULES)
            if cat:
                rows.append((s, cat))
            else:
                unmatched += 1
        cur.executemany("""INSERT INTO subject_category_map (subject, category)
                           VALUES (%s,%s) ON CONFLICT (subject) DO UPDATE
                           SET category=EXCLUDED.category WHERE NOT subject_category_map.reviewed""",
                        rows)
    conn.commit()
    log(f"subjects mapped: {len(rows):,}   unmatched (left as 'other'): {unmatched:,}")


def classify_donors(conn) -> None:
    with conn.cursor() as cur:
        # Only donors whose money actually reaches a legislator matter for matching.
        cur.execute("""SELECT donor_name, count(*), sum(amount) FROM contributions
                       WHERE recipient_legislator_id IS NOT NULL AND donor_name IS NOT NULL
                       GROUP BY 1""")
        donors = cur.fetchall()
        rows, unmatched = [], 0
        for name, _cnt, _amt in donors:
            cat, conf = first_match(name, DONOR_RULES)
            if cat:
                rows.append((name, cat, conf))
            else:
                unmatched += 1
        cur.executemany("""INSERT INTO donor_category_map (donor_name, category, confidence)
                           VALUES (%s,%s,%s) ON CONFLICT (donor_name) DO UPDATE
                           SET category=EXCLUDED.category, confidence=EXCLUDED.confidence
                           WHERE NOT donor_category_map.reviewed""", rows)
    conn.commit()
    log(f"donors mapped: {len(rows):,}   unmatched: {unmatched:,} (of {len(donors):,})")


def export_review(conn, limit: int = 200) -> Path:
    """The 200 largest donor entities, for the human review PLAN.md Phase 6 asks for."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.donor_name, count(*) AS n, sum(c.amount) AS total,
                   m.category, m.confidence, m.reviewed
            FROM contributions c
            LEFT JOIN donor_category_map m ON m.donor_name = c.donor_name
            WHERE c.recipient_legislator_id IS NOT NULL AND c.donor_name IS NOT NULL
            GROUP BY 1,4,5,6 ORDER BY 3 DESC LIMIT %s""", (limit,))
        rows = cur.fetchall()
    out = config.PROJECT_ROOT / "data" / "processed" / "donor_categories_to_review.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["correct_category", "donor_name", "contributions", "total_dollars",
                    "proposed_category", "confidence", "already_reviewed"])
        for name, n, total, cat, conf, rev in rows:
            w.writerow(["", name, n, f"{total:.2f}", cat or "UNMATCHED", conf or "", rev])
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("subjects"); sub.add_parser("donors")
    r = sub.add_parser("review"); r.add_argument("--limit", type=int, default=200)
    args = p.parse_args(argv)

    with psycopg.connect(config.require("DATABASE_URL")) as conn:
        if args.cmd == "subjects":
            classify_subjects(conn)
        elif args.cmd == "donors":
            classify_donors(conn)
        elif args.cmd == "review":
            path = export_review(conn, args.limit)
            log(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
