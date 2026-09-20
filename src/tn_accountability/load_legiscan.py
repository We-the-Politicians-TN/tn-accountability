"""Load downloaded LegiScan session archives into Postgres.

    python -m tn_accountability.load_legiscan              # all downloaded sessions
    python -m tn_accountability.load_legiscan --replace    # reload

Reads the ZIPs in data/raw/legiscan/ without unpacking them, so the evidence trail
stays a single immutable file per session.

Load order matters: people, then bills, then sponsorships and roll calls, because
sponsorships reference both a bill and a legislator.

People are keyed on LegiScan's `people_id`, which is stable across sessions, so a
member serving several General Assemblies is one row in `legislators` with several
rows in `legislator_terms`.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

import psycopg

from . import config
from .legiscan import log

# LegiScan reference values. Spelled out rather than inlined as magic numbers,
# because silently mislabelling a vote would corrupt the analysis invisibly.
SPONSOR_TYPE = {0: "cosponsor", 1: "primary", 2: "cosponsor", 3: "cosponsor"}
# LegiScan publishes both long and short forms ('Not Voting' and 'NV'), so both
# are mapped. Anything unmapped is stored as 'other' AND reported at the end of a
# load — a silently mislabelled vote would corrupt the analysis invisibly.
VOTE_TEXT = {"yea": "yea", "yes": "yea", "aye": "yea",
             "nay": "nay", "no": "nay",
             "not voting": "not_voting", "nv": "not_voting",
             "absent": "absent", "abs": "absent",
             "present": "present"}
BILL_STATUS = {1: "introduced", 2: "engrossed", 3: "enrolled",
               4: "passed", 5: "vetoed", 6: "failed"}
ROLE_CHAMBER = {"Rep": "house", "Sen": "senate"}


def norm(t):
    return " ".join(t.split()).upper() if t else None


def district_number(raw):
    """'HD-044' -> '44'. Keeps anything unrecognised as-is rather than guessing."""
    if not raw:
        return None
    m = re.search(r"(\d+)", raw)
    return str(int(m.group(1))) if m else raw


def parse_date(raw):
    if not raw:
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def introduced_date(bill):
    """Earliest history entry. LegiScan has no explicit introduction date field."""
    dates = [parse_date(h.get("date")) for h in bill.get("history") or []]
    dates = [d for d in dates if d]
    return min(dates) if dates else None


def passed_date(bill):
    """Date of the history entry where the bill reached passed status."""
    for h in bill.get("history") or []:
        text = (h.get("action") or "").lower()
        if "signed by governor" in text or "public chapter" in text:
            return parse_date(h.get("date"))
    return None


class Archive:
    """One session ZIP, read without unpacking."""

    def __init__(self, path: Path):
        self.path = path
        self.zf = zipfile.ZipFile(path)
        self.names = self.zf.namelist()

    def _records(self, kind: str, key: str):
        for n in self.names:
            if f"/{kind}/" in n and n.endswith(".json"):
                obj = json.loads(self.zf.read(n)).get(key)
                if obj:
                    yield obj, n

    people = lambda self: self._records("people", "person")
    bills = lambda self: self._records("bill", "bill")
    votes = lambda self: self._records("vote", "roll_call")


class Loader:
    def __init__(self, conn, pull_id: int):
        self.conn = conn
        self.pull_id = pull_id
        self.people_ids = {}   # legiscan people_id -> legislators.id
        self.bill_ids = {}     # legiscan bill_id   -> bills.id

    # -- people ---------------------------------------------------------------

    def load_people(self, arc: Archive, session: dict) -> int:
        rows = []
        for p, _ in arc.people():
            rows.append((
                p["people_id"], p.get("name"), norm(p.get("name")),
                p.get("first_name") or None, p.get("middle_name") or None,
                p.get("last_name") or None, p.get("suffix") or None,
                p.get("nickname") or None, p.get("party") or None,
                ROLE_CHAMBER.get(p.get("role")), district_number(p.get("district")),
                p.get("role") or None, p.get("person_hash") or None,
                p.get("ballotpedia") or None, p.get("opensecrets_id") or None,
                p.get("votesmart_id") or None, self.pull_id,
            ))
        with self.conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO legislators (legiscan_people_id, full_name_raw, full_name,
                    first_name, middle_name, last_name, suffix, nickname, party,
                    chamber, district, role_raw, person_hash, ballotpedia_url,
                    opensecrets_id, votesmart_id, data_pull_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::chamber,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (legiscan_people_id) DO UPDATE SET
                    full_name_raw=EXCLUDED.full_name_raw, full_name=EXCLUDED.full_name,
                    party=EXCLUDED.party, chamber=EXCLUDED.chamber,
                    district=EXCLUDED.district, person_hash=EXCLUDED.person_hash,
                    updated_at=now()
            """, rows)
            cur.execute("SELECT legiscan_people_id, id FROM legislators WHERE legiscan_people_id IS NOT NULL")
            self.people_ids = dict(cur.fetchall())

        # Terms: derived from session membership, NOT certified term dates. See 0005.
        ga = re.search(r"(\d+)", session.get("session_name", "") or "")
        term_rows = [
            (self.people_ids[p["people_id"]], ROLE_CHAMBER.get(p.get("role")),
             district_number(p.get("district")) or "?", p.get("party") or None,
             int(ga.group(1)) if ga else None,
             f"{session['year_start']}-01-01", f"{session['year_end']}-12-31",
             "legiscan_session", self.pull_id)
            for p, _ in arc.people()
            if p["people_id"] in self.people_ids and ROLE_CHAMBER.get(p.get("role"))
        ]
        with self.conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO legislator_terms (legislator_id, chamber, district, party,
                    general_assembly, start_date, end_date, source, data_pull_id)
                SELECT %s,%s::chamber,%s,%s,%s,%s::date,%s::date,%s,%s
                WHERE NOT EXISTS (
                    SELECT 1 FROM legislator_terms
                    WHERE legislator_id=%s AND general_assembly=%s)
            """, [r + (r[0], r[4]) for r in term_rows])
        return len(rows)

    # -- bills ----------------------------------------------------------------

    def load_bills(self, arc: Archive) -> int:
        rows = []
        for b, _ in arc.bills():
            sess = b.get("session") or {}
            ga = re.search(r"(\d+)", sess.get("session_name", "") or "")
            rows.append((
                b["bill_id"], sess.get("session_name"),
                int(ga.group(1)) if ga else None, sess.get("year_start"),
                sess.get("session_id"), b.get("bill_number"), b.get("bill_type"),
                b.get("bill_type"), b.get("title"), b.get("description"),
                [s.get("subject_name") for s in b.get("subjects") or []],
                (b.get("committee") or {}).get("name") or None,
                introduced_date(b),
                (b.get("history") or [{}])[-1].get("action") if b.get("history") else None,
                parse_date(b.get("status_date")),
                BILL_STATUS.get(b.get("status")), str(b.get("status")),
                b.get("status") == 4, passed_date(b),
                bool(b.get("completed")), b.get("change_hash"),
                b.get("url"), b.get("state_link"), self.pull_id,
            ))
        with self.conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO bills (legiscan_bill_id, session_name, general_assembly,
                    session_year_start, session_id, bill_number, bill_type, bill_type_raw,
                    title, description, subjects, committee, introduced_date, last_action,
                    last_action_date, status, status_raw, passed, passed_date, completed,
                    change_hash, legiscan_url, state_url, data_pull_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (legiscan_bill_id) DO UPDATE SET
                    title=EXCLUDED.title, status=EXCLUDED.status, passed=EXCLUDED.passed,
                    passed_date=EXCLUDED.passed_date, last_action=EXCLUDED.last_action,
                    last_action_date=EXCLUDED.last_action_date,
                    change_hash=EXCLUDED.change_hash, updated_at=now()
            """, rows)
            cur.execute("SELECT legiscan_bill_id, id FROM bills")
            self.bill_ids = dict(cur.fetchall())
        return len(rows)

    def load_sponsorships(self, arc: Archive) -> int:
        rows = []
        for b, _ in arc.bills():
            bid = self.bill_ids.get(b["bill_id"])
            if not bid:
                continue
            for s in b.get("sponsors") or []:
                lid = self.people_ids.get(s.get("people_id"))
                if lid:
                    rows.append((bid, lid, SPONSOR_TYPE.get(s.get("sponsor_type_id"), "cosponsor"),
                                 s.get("sponsor_order"), self.pull_id))
        with self.conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO sponsorships (bill_id, legislator_id, sponsor_type,
                                          sponsor_order, data_pull_id)
                VALUES (%s,%s,%s::sponsor_type,%s,%s)
                ON CONFLICT (bill_id, legislator_id, sponsor_type) DO NOTHING
            """, rows)
        return len(rows)

    def load_votes(self, arc: Archive):
        rc_rows, missing_bill = [], 0
        for v, _ in arc.votes():
            bid = self.bill_ids.get(v.get("bill_id"))
            if not bid:
                missing_bill += 1
                continue
            rc_rows.append((v["roll_call_id"], bid, v.get("bill_id"), parse_date(v.get("date")),
                            v.get("desc"), {"H": "house", "S": "senate"}.get(v.get("chamber")),
                            v.get("yea"), v.get("nay"), v.get("nv"), v.get("absent"),
                            v.get("total"), bool(v.get("passed")), self.pull_id))
        with self.conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO roll_calls (legiscan_roll_call_id, bill_id, legiscan_bill_id,
                    vote_date, description, chamber, yea, nay, not_voting, absent,
                    total, passed, data_pull_id)
                VALUES (%s,%s,%s,%s,%s,%s::chamber,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (legiscan_roll_call_id) DO NOTHING
            """, rc_rows)
            cur.execute("SELECT legiscan_roll_call_id, id FROM roll_calls")
            rc_ids = dict(cur.fetchall())

        v_rows, unknown_vote = [], set()
        for v, _ in arc.votes():
            rcid = rc_ids.get(v["roll_call_id"])
            bid = self.bill_ids.get(v.get("bill_id"))
            if not (rcid and bid):
                continue
            for iv in v.get("votes") or []:
                lid = self.people_ids.get(iv.get("people_id"))
                if not lid:
                    continue
                text = (iv.get("vote_text") or "").strip().lower()
                mapped = VOTE_TEXT.get(text)
                if not mapped:
                    unknown_vote.add(text)
                    mapped = "other"
                v_rows.append((rcid, bid, lid, mapped, iv.get("vote_text"), self.pull_id))
        with self.conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO votes (roll_call_id, bill_id, legislator_id, vote, vote_raw, data_pull_id)
                VALUES (%s,%s,%s,%s::vote_cast,%s,%s)
                ON CONFLICT (roll_call_id, legislator_id) DO NOTHING
            """, v_rows)
        return len(rc_rows), len(v_rows), missing_bill, unknown_vote


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--replace", action="store_true")
    args = p.parse_args(argv)

    raw = config.RAW_DIR / "legiscan"
    index = json.loads((raw / "_datasets.json").read_text())
    archives = sorted(index.values(), key=lambda m: m["year_start"])
    log(f"sessions downloaded: {len(archives)}")

    with psycopg.connect(config.require("DATABASE_URL")) as conn:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO data_pulls (source, search_type, source_files, notes)
                           VALUES ('legiscan','session_archive',%s,%s) RETURNING id""",
                        ([m["file"] for m in archives],
                         f"load of {len(archives)} LegiScan session archives"))
            pull_id = cur.fetchone()[0]
        conn.commit()

        loader = Loader(conn, pull_id)
        totals = dict(people=0, bills=0, sponsorships=0, roll_calls=0, votes=0)
        all_unknown = set()

        for meta in archives:
            path = raw / meta["file"]
            log(f"{meta['session_name']} ({meta['year_start']}-{meta['year_end']})")
            arc = Archive(path)
            session = {"session_name": meta["session_name"],
                       "year_start": meta["year_start"], "year_end": meta["year_end"]}
            n = loader.load_people(arc, session);      totals["people"] += n;   log(f"  people       {n:>6,}")
            n = loader.load_bills(arc);                totals["bills"] += n;    log(f"  bills        {n:>6,}")
            n = loader.load_sponsorships(arc);         totals["sponsorships"] += n; log(f"  sponsorships {n:>6,}")
            rc, vt, missing, unknown = loader.load_votes(arc)
            totals["roll_calls"] += rc; totals["votes"] += vt; all_unknown |= unknown
            log(f"  roll calls   {rc:>6,}")
            log(f"  votes        {vt:>6,}")
            if missing:
                log(f"  NOTE: {missing} roll calls referenced a bill not in this archive")
            conn.commit()

        with conn.cursor() as cur:
            cur.execute("""UPDATE data_pulls SET status='success', finished_at=now(), rows_added=%s
                           WHERE id=%s""", (sum(totals.values()), pull_id))
        conn.commit()

    log("totals: " + ", ".join(f"{k}={v:,}" for k, v in totals.items()))
    if all_unknown:
        log(f"UNMAPPED vote text (stored as 'other'): {sorted(all_unknown)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
