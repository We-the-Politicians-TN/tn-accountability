"""Match legislators to the candidate names TREF files their money under.

    python -m tn_accountability.match_tref propose      # score and write proposals
    python -m tn_accountability.match_tref review       # export the ones needing a human
    python -m tn_accountability.match_tref apply FILE   # apply an approved CSV

This is the bridge between the money and the legislating. Until it runs, every
`recipient_legislator_id` is null and the two halves of the database are unconnected.

**Confidence here measures ambiguity, not string similarity.** TREF publishes no
district or office alongside the recipient name, so the only signal is the name
itself — and Tennessee has three sitting Brookses, three Johnsons, three Joneses, and
two simultaneous Hills. A name that matches one legislator at 95% is a different
proposition from one that matches two at 95% each. The score is therefore reduced by
how close the runner-up is, so genuine ambiguity can never be auto-approved however
good the raw string match looks.

Nothing is applied to the data without approval except matches that are BOTH
high-scoring AND unambiguous. Everything else goes to a review file.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import psycopg
from rapidfuzz import fuzz

from . import config
from .legiscan import log

AUTO_SCORE = 92     # raw similarity needed before auto-approval is even considered
AUTO_MARGIN = 15    # ...and this much clear of the runner-up
REVIEW_FLOOR = 70   # below this, not worth a human's time

# Names that are organisations rather than people. A legislator's own PAC is a
# separate legal entity from their candidate committee, so matching "GARRETT PAC"
# to Johnny Garrett would silently merge two different filers.
ORG_PATTERN = re.compile(
    r"\b(PAC|PCC|COMMITTEE|COMMITTE|FUND|ASSOCIATION|ASSN|UNION|CORP|CORPORATION|"
    r"INC|LLC|COMPANY|CO\.|PARTY|CAUCUS|COALITION|COUNCIL|SOCIETY|LEAGUE|"
    r"FEDERATION|ALLIANCE|TRUST|GROUP|EMPLOYEES|WORKERS|LOCAL)\b")

PERSON_PATTERN = re.compile(r"^[A-Z][A-Z .'\-]+,\s*[A-Z]")


SUFFIXES = {"JR", "JR.", "SR", "SR.", "II", "III", "IV", "V", "MD", "M.D.", "DDS", "PHD"}


def split_tref_name(name: str):
    """'LAMBERTH, II, WILLIAM G.' -> ('LAMBERTH', ['WILLIAM','G']).

    TREF puts suffixes in their own comma-separated field, and uses full legal names
    where a member is known by a middle name or a diminutive. Both are stripped here
    so the comparison is surname-against-surname and given-names-against-given-names.
    """
    parts = [p.strip().upper() for p in name.split(",") if p.strip()]
    parts = [p for p in parts if p.rstrip(".") not in {x.rstrip(".") for x in SUFFIXES}]
    if not parts:
        return "", []
    last = parts[0]
    givens = []
    for chunk in parts[1:]:
        givens.extend(t for t in re.split(r"[\s.]+", chunk) if t)
    return last, givens


def variants(leg: dict) -> list:
    """Every plausible way TREF might file this legislator's name."""
    last = (leg["last_name"] or "").upper().strip()
    if not last:
        return []
    firsts = {f.upper().strip() for f in (leg["first_name"], leg["nickname"]) if f}
    out = set()
    for f in firsts:
        out.add(f"{last}, {f}")
        if leg["middle_name"]:
            out.add(f"{last}, {f} {leg['middle_name'].upper().strip()}")
            out.add(f"{last}, {f} {leg['middle_name'][0].upper()}")
        if leg["suffix"]:
            out.add(f"{last} {leg['suffix'].upper()}, {f}")
    return sorted(out)


def score(tref_name: str, leg: dict) -> int:
    """Similarity, weighted so the surname dominates.

    Whole-string similarity was letting a shared FIRST name carry an unrelated
    surname: 'LEE, BILL' (Governor Bill Lee, not a legislator) scored 57 against
    'Bill Beck' purely on the shared 'BILL'. The surname is the load-bearing
    signal, so a surname mismatch now caps the whole score.

    TREF contains many non-legislators — governors, mayors, local candidates. For
    those the correct output is a low score and no match, not a forced best guess.
    """
    t_last, t_givens = split_tref_name(tref_name)
    l_last = (leg["last_name"] or "").upper().strip()
    if not t_last or not l_last:
        return 0

    last_s = int(fuzz.ratio(t_last, l_last))
    if last_s < 85:
        # Different family name: cap low so it can never reach auto-approval, while
        # still surfacing for review if the given names align.
        return min(last_s, 60)

    # Given names: TREF may hold a formal first name where the member goes by a
    # middle name or diminutive (WILLIAM BROCK -> Brock; JACOB -> Jake). Compare
    # every TREF given-name token against every known form and keep the best.
    known = {v.upper().strip() for v in
             (leg["first_name"], leg["nickname"], leg["middle_name"]) if v}
    if not known or not t_givens:
        given_s = 50
    else:
        given_s = max(int(fuzz.ratio(t, k)) for t in t_givens for k in known)
        # An exact token match anywhere is strong evidence, even amid extra names.
        if any(t == k for t in t_givens for k in known):
            given_s = max(given_s, 97)

    return int(round(last_s * 0.65 + given_s * 0.35))


def load_inputs(conn):
    with conn.cursor() as cur:
        cur.execute("""SELECT id, full_name_raw, first_name, middle_name, last_name,
                              suffix, nickname, party, chamber::text, district
                       FROM legislators WHERE last_name IS NOT NULL""")
        cols = [d[0] for d in cur.description]
        legs = [dict(zip(cols, r)) for r in cur.fetchall()]

        # Recipient names carrying real money, and how much — so review effort can be
        # spent where it matters.
        cur.execute("""SELECT recipient_name, count(*), coalesce(sum(amount),0)
                       FROM contributions WHERE recipient_name IS NOT NULL
                       GROUP BY 1""")
        recips = cur.fetchall()
    return legs, recips


def propose(conn, write: bool = True):
    legs, recips = load_inputs(conn)
    log(f"legislators: {len(legs)}   distinct TREF recipient names: {len(recips):,}")

    auto, review, orgs, skipped = [], [], 0, 0
    for name, n_rows, total in recips:
        if ORG_PATTERN.search(name):
            orgs += 1
            continue
        if not PERSON_PATTERN.match(name):
            skipped += 1
            continue

        scored = sorted(((score(name, l), l) for l in legs), key=lambda x: -x[0])
        best_s, best = scored[0]
        second_s = scored[1][0] if len(scored) > 1 else 0
        margin = best_s - second_s

        if best_s < REVIEW_FLOOR:
            continue

        # Confidence is the raw score discounted by how close the runner-up is.
        confidence = round(max(0.0, best_s - max(0, AUTO_MARGIN - margin) * 2.0), 2)
        rival = scored[1][1]["full_name_raw"] if len(scored) > 1 and second_s >= REVIEW_FLOOR else ""

        row = dict(tref_name=name, rows=n_rows, total=float(total),
                   legislator_id=best["id"], legislator=best["full_name_raw"],
                   party=best["party"], chamber=best["chamber"], district=best["district"],
                   raw_score=best_s, runner_up=rival, runner_up_score=second_s,
                   margin=margin, confidence=confidence)

        if best_s >= AUTO_SCORE and margin >= AUTO_MARGIN:
            row["decision"] = "auto"
            auto.append(row)
        else:
            row["decision"] = "review"
            review.append(row)

    log(f"organisation names skipped : {orgs:,}")
    log(f"non-person names skipped   : {skipped:,}")
    log(f"auto-approvable            : {len(auto):,}")
    log(f"need human review          : {len(review):,}")

    if write:
        with conn.cursor() as cur:
            # Clear proposals from earlier runs before writing new ones. Without this,
            # re-running after a scoring change leaves the old (wrong) match in place
            # alongside the new one, because the conflict key includes legislator_id —
            # so one TREF name ends up proposed against two different legislators and a
            # later bulk approval could sweep in the discarded one.
            # Human-approved rows are preserved: they carry approved_by.
            cur.execute("DELETE FROM legislator_tref_ids WHERE approved_by IS NULL")
            log(f"cleared {cur.rowcount:,} superseded proposal(s) from earlier runs")
            for r in auto + review:
                cur.execute("""
                    INSERT INTO legislator_tref_ids (legislator_id, tref_name_raw, tref_name,
                        match_confidence, match_method, approved, notes, data_pull_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,NULL)
                    ON CONFLICT (legislator_id, tref_name) DO UPDATE SET
                        match_confidence=EXCLUDED.match_confidence,
                        match_method=EXCLUDED.match_method, notes=EXCLUDED.notes
                """, (r["legislator_id"], r["tref_name"], r["tref_name"], r["confidence"],
                      f"fuzzy raw={r['raw_score']} margin={r['margin']}",
                      r["decision"] == "auto",
                      f"{r['rows']} rows, ${r['total']:,.0f}" +
                      (f"; runner-up {r['runner_up']} @{r['runner_up_score']}" if r["runner_up"] else "")))
        conn.commit()
    return auto, review


def write_csv(rows, path: Path, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("propose")
    sub.add_parser("review")
    sub.add_parser("link", help="apply APPROVED matches to contributions/expenditures")
    a = sub.add_parser("apply"); a.add_argument("file", type=Path)
    args = p.parse_args(argv)

    out_dir = config.PROJECT_ROOT / "data" / "processed"

    with psycopg.connect(config.require("DATABASE_URL")) as conn:
        if args.cmd in ("propose", "review"):
            auto, review = propose(conn, write=(args.cmd == "propose"))
            for r in review:
                r["approve"] = ""        # human writes Y here
            fields = ["approve", "decision", "tref_name", "legislator", "party", "chamber", "district",
                      "confidence", "raw_score", "margin", "runner_up", "runner_up_score",
                      "rows", "total", "legislator_id"]
            review.sort(key=lambda r: -r["total"])
            write_csv(review, out_dir / "tref_matches_to_review.csv", fields)
            write_csv(auto, out_dir / "tref_matches_auto.csv", fields)
            log(f"wrote {out_dir/'tref_matches_to_review.csv'}")
            log(f"wrote {out_dir/'tref_matches_auto.csv'}")
            if review:
                log("\nhighest-value matches needing review:")
                for r in review[:10]:
                    rival = f"  vs {r['runner_up']}@{r['runner_up_score']}" if r["runner_up"] else ""
                    log(f"  ${r['total']:>12,.0f}  {r['tref_name'][:28]:<29} -> "
                        f"{r['legislator'][:24]:<25} conf={r['confidence']:.0f}{rival}")

        elif args.cmd == "link":
            # Only approved matches are ever applied. Unapproved proposals must not
            # reach a published figure — see D8 and the approved flag's comment.
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE contributions c SET recipient_legislator_id = t.legislator_id
                    FROM legislator_tref_ids t
                    WHERE t.approved AND c.recipient_name = t.tref_name
                      AND c.recipient_legislator_id IS DISTINCT FROM t.legislator_id
                """)
                log(f"contributions linked: {cur.rowcount:,}")
                cur.execute("""
                    UPDATE expenditures e SET spender_legislator_id = t.legislator_id
                    FROM legislator_tref_ids t
                    WHERE t.approved AND e.spender_name = t.tref_name
                      AND e.spender_legislator_id IS DISTINCT FROM t.legislator_id
                """)
                log(f"expenditures linked: {cur.rowcount:,}")
            conn.commit()

        elif args.cmd == "apply":
            with open(args.file, newline="") as fh:
                rows = [r for r in csv.DictReader(fh)
                        if (r.get("approve") or "").strip().lower() in ("y", "yes", "1", "true")]
            with conn.cursor() as cur:
                for r in rows:
                    cur.execute("""UPDATE legislator_tref_ids
                                   SET approved=true, approved_at=now(), approved_by='human review'
                                   WHERE legislator_id=%s AND tref_name=%s""",
                                (int(r["legislator_id"]), r["tref_name"]))
            conn.commit()
            log(f"approved {len(rows)} match(es) from {args.file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
