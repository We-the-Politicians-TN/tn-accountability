"""Lobbying Expenditure Reports (SS-8011) and employer registrations from iLobby.

    python -m tn_accountability.tec_lobby fetch --years 2025

Every employer of lobbyists files a registration and two expenditure reports a year.
Each report states the employer's nature of business as subject matters ("health &
health care; insurance") — the authoritative employer -> industry mapping that
replaces name-pattern guessing (D80, D95). Dollar figures are ranges only, and there
is no per-legislator detail (docs/influence_channels.md, channel 2).

Fetch only: saves listing, dashboard and report HTML under data/raw/tec/lobby/ with
a SHA-256 manifest. Files already on disk are never rewritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import config
from .backfill import parse_years
from .legiscan import log
from .tec_soi import _retrying, _clean

BASE = "https://ilobbysearch.app.tn.gov/ilobbysearch"
RAW = config.RAW_DIR / "tec" / "lobby"
UA = "tn-accountability/0.1 (public records research; github.com/We-the-Politicians-TN/tn-accountability)"


def _sleep():
    time.sleep(random.uniform(0.7, 1.4))


def _get(s, path, what):
    r = _retrying(lambda: s.get(f"{BASE}/{path}", timeout=90), what)
    r.raise_for_status()
    return r.text


def fetch(years) -> None:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    for year in years:
        d = RAW / str(year)
        (d / "dashboards").mkdir(parents=True, exist_ok=True)
        (d / "reports").mkdir(parents=True, exist_ok=True)
        log(f"{year}: listing employers")
        _retrying(lambda: s.get(f"{BASE}/search.htm", timeout=60).raise_for_status(), "init")
        _sleep()
        r = _retrying(lambda: s.post(f"{BASE}/search.htm", timeout=120, data={
            "request": "employerSearch", "employerName": "",
            "employerSubjectMatter": "0", "employerYear": str(year)}), "employer list")
        r.raise_for_status()
        (d / "employers.html").write_text(r.text)
        employers = []
        for row in re.findall(r'<tr[^>]*>(.*?)</tr>', r.text, flags=re.S):
            m = re.search(r'viewEmployerDashboard\.htm\?employerId=(\d+)', row)
            if not m:
                continue
            cells = [_clean(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', row, flags=re.S)]
            employers.append(dict(employer_id=int(m.group(1)), name=cells[0] if cells else "",
                                  city=cells[2] if len(cells) > 2 else "", state=cells[3] if len(cells) > 3 else ""))
        log(f"  {len(employers)} employers")

        manifest = dict(year=year, fetched_at=datetime.now(timezone.utc).isoformat(), employers=[])
        n_dash = n_rep = 0
        for i, e in enumerate(employers, 1):
            dash = d / "dashboards" / f"{e['employer_id']}.html"
            if not dash.exists():
                _sleep()
                dash.write_text(_get(s, f"viewEmployerDashboard.htm?employerId={e['employer_id']}",
                                     f"dashboard {e['employer_id']}"))
                n_dash += 1
            html = dash.read_text()
            # Current report is a link; archived ones are <option value=reportId>End Year 2025</option>.
            reports = {}
            cur = re.search(r'Current:\s*<a\s+href="viewExpenditureReport\.htm\?reportId=(\d+)"', html, flags=re.S)
            if cur:
                reports[int(cur.group(1))] = "current"
            # The option VALUE is the relative report URL, not a bare id, and the label
            # spans lines — the first version of this regex matched nothing (D109).
            for rid, label in re.findall(
                    r'<option[^>]+value="viewExpenditureReport\.htm\?reportId=(\d+)"[^>]*>\s*((?:End|Mid) Year \d{4})\s*</option>',
                    html, flags=re.S):
                if str(year) in label:
                    reports[int(rid)] = label
            e["dashboard"] = dash.name
            e["reports"] = []
            for rid, label in reports.items():
                rep = d / "reports" / f"{rid}.html"
                if not rep.exists():
                    _sleep()
                    rep.write_text(_get(s, f"viewExpenditureReport.htm?reportId={rid}", f"report {rid}"))
                    n_rep += 1
                e["reports"].append(dict(report_id=rid, label=label, file=rep.name,
                                         sha256=hashlib.sha256(rep.read_bytes()).hexdigest()))
            manifest["employers"].append(e)
            if i % 25 == 0:
                log(f"  {i}/{len(employers)} employers, {n_dash} dashboards + {n_rep} reports fetched so far")
                (d / "_manifest.json").write_text(json.dumps(manifest, indent=1))
        (d / "_manifest.json").write_text(json.dumps(manifest, indent=1))
        log(f"  done {year}: {n_dash} dashboards, {n_rep} reports fetched")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch"); f.add_argument("--years", default="2025")
    a = p.parse_args(argv)
    fetch(parse_years(a.years))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
