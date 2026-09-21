"""In-state events hosted for the General Assembly (Ethics Commission, 2006-2026).

    python -m tn_accountability.tec_events fetch
    python -m tn_accountability.tec_events load

One HTML table per year. Sponsor-level only: attendees are never recorded, so an
event is never attributed to a member (docs/influence_channels.md, channel 1).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import requests

from . import config
from .legiscan import log
from .tec_soi import _retrying, _clean

RAW = config.RAW_DIR / "tec" / "events"
UA = "tn-accountability/0.1 (public records research; github.com/We-the-Politicians-TN/tn-accountability)"
BASE = "https://www.tn.gov/tec/tec-lobbyist/tec-in-state-events"


def url_for(year: int) -> str:
    # The Commission changed the slug in 2018: older years carry a 'tec-' prefix.
    return f"{BASE}/{'tec-' if year <= 2017 else ''}{year}-in-state-events.html"


def fetch(years=range(2006, 2027)) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    s = requests.Session(); s.headers["User-Agent"] = UA
    manifest = {}
    for y in years:
        f = RAW / f"{y}.html"
        if not f.exists():
            r = _retrying(lambda y=y: s.get(url_for(y), timeout=60), f"events {y}")
            if r.status_code == 404:
                log(f"  {y}: no page (404)"); continue
            r.raise_for_status()
            f.write_text(r.text); time.sleep(1.0)
        manifest[y] = dict(file=f.name, url=url_for(y), sha256=hashlib.sha256(f.read_bytes()).hexdigest(),
                           rows=len(parse_year(f.read_text(), y)))
        log(f"  {y}: {manifest[y]['rows']} events")
    (RAW / "_manifest.json").write_text(json.dumps(dict(fetched_at=datetime.now(timezone.utc).isoformat(),
                                                        years=manifest), indent=1))


MONEY = re.compile(r'[^0-9.\-]')


def parse_year(html: str, year: int) -> list:
    out = []
    for i, row in enumerate(re.findall(r'<tr[^>]*>(.*?)</tr>', html, flags=re.S)):
        cells_html = re.findall(r'<td[^>]*>(.*?)</td>', row, flags=re.S)
        if len(cells_html) < 5:
            continue
        cells = [_clean(c) for c in cells_html]
        links = [re.sub(r'&amp;', '&', h) for h in re.findall(r'href="([^"]+)"', row)]
        docs = [h if h.startswith('http') else 'https://www.tn.gov' + h for h in links]
        inv = next((d for d in docs if 'eventid' in d.lower() or 'invit' in d.lower()), None)
        dis = next((d for d in docs if 'disclosure' in d.lower()), None)
        m = re.match(r'(\d{4}-\d{2}-\d{2})', cells[0])
        def money(x):
            v = MONEY.sub('', x or '')
            try: return float(v) if v not in ('', '-', '.') else None
            except ValueError: return None
        out.append(dict(row_index=i, event_date_raw=cells[0], event_date=m.group(1) if m else None,
                        event_name_raw=cells[1], sponsor_raw=cells[2], sponsor=' '.join(cells[2].split()).upper(),
                        total_expense_raw=cells[3], total_expense=money(cells[3]),
                        per_person_raw=cells[4], per_person=money(cells[4]),
                        invitation_url=inv, disclosure_url=dis))
    return out


def load(conn) -> None:
    man = json.loads((RAW / "_manifest.json").read_text())["years"]
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO data_pulls (source, search_type, source_files, notes)
                       VALUES ('tn_ethics_commission','in_state_events',%s,%s) RETURNING id""",
                    ([f"data/raw/tec/events/{v['file']}" for v in man.values()], f"{len(man)} year pages"))
        pull = cur.fetchone()[0]
        n = 0
        for y, v in man.items():
            src = f"data/raw/tec/events/{v['file']}"
            for e in parse_year((RAW / v["file"]).read_text(), int(y)):
                cur.execute("""INSERT INTO sponsored_events (event_year, event_date_raw, event_date, event_name_raw,
                                 sponsor_raw, sponsor, total_expense_raw, total_expense, per_person_raw, per_person,
                                 invitation_url, disclosure_url, source_file, row_index, data_pull_id)
                               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                               ON CONFLICT (source_file, row_index) DO NOTHING""",
                            (int(y), e["event_date_raw"], e["event_date"], e["event_name_raw"], e["sponsor_raw"],
                             e["sponsor"], e["total_expense_raw"], e["total_expense"], e["per_person_raw"],
                             e["per_person"], e["invitation_url"], e["disclosure_url"], src, e["row_index"], pull))
                n += cur.rowcount
        cur.execute("UPDATE data_pulls SET status='success', finished_at=now(), rows_added=%s WHERE id=%s", (n, pull))
    conn.commit()
    log(f"loaded {n} events")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["fetch", "load"])
    a = p.parse_args(argv)
    if a.cmd == "fetch":
        fetch(); return 0
    with psycopg.connect(config.require("DATABASE_URL")) as conn:
        load(conn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
