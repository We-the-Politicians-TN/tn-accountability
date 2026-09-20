"""Fetch Tennessee legislative data from LegiScan.

    python -m tn_accountability.legiscan list          # sessions and sizes, 1 call
    python -m tn_accountability.legiscan fetch --from-year 2019

Uses bulk dataset endpoints only. One `getDataset` call returns an entire session —
every bill, sponsor, roll call and person — as a base64 ZIP. Fetching 2019 to date
costs 5 calls against a 30,000/month quota; the per-bill `getBill` equivalent would
be several thousand.

Two safeguards, matching what was stated on the API key application:
  - every request is counted and logged, with a hard per-run ceiling
  - a session is re-downloaded only when its `dataset_hash` has changed

Raw ZIPs are written to data/raw/legiscan/ and never modified. They are the
evidence trail for every bill and vote the site publishes.

LegiScan data is licensed CC BY 4.0. Any page presenting it must credit LegiScan
and link the licence. See D45 in STATUS.md.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

from . import config

API = "https://api.legiscan.com/"
STATE = "TN"
# Generous for bulk use (a full backfill is 5 calls) but low enough that a bug
# cannot burn the monthly quota before anyone notices.
MAX_CALLS_PER_RUN = 50


def log(msg: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


class QuotaExceeded(RuntimeError):
    pass


class LegiScanClient:
    def __init__(self, out_dir: Path = None, max_calls: int = MAX_CALLS_PER_RUN):
        self.key = config.require("LEGISCAN_API_KEY")
        self.out_dir = out_dir or (config.RAW_DIR / "legiscan")
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.max_calls = max_calls
        self.calls = 0
        self.session = requests.Session()
        self.session.headers["User-Agent"] = (
            "tn-accountability/0.1 (+https://github.com/We-the-Politicians-TN/tn-accountability)")

    def _call(self, op: str, **params):
        """One API request, counted against the run ceiling."""
        if self.calls >= self.max_calls:
            raise QuotaExceeded(
                f"hit the {self.max_calls}-call ceiling for this run. Raise --max-calls "
                f"deliberately if that is really needed.")
        self.calls += 1
        r = self.session.get(API, params={"key": self.key, "op": op, **params}, timeout=180)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "OK":
            raise RuntimeError(f"{op} failed: {data.get('alert') or data}")
        log(f"  api call {self.calls}/{self.max_calls}: {op}")
        return data

    def dataset_list(self) -> list:
        return self._call("getDatasetList", state=STATE)["datasetlist"]

    def _index_path(self) -> Path:
        return self.out_dir / "_datasets.json"

    def _index(self) -> dict:
        p = self._index_path()
        return json.loads(p.read_text()) if p.exists() else {}

    def fetch_dataset(self, meta: dict, force: bool = False) -> dict:
        """Download one session archive. Skips when the hash is unchanged."""
        sid = str(meta["session_id"])
        index = self._index()
        prior = index.get(sid)
        zip_path = self.out_dir / f"TN_{meta['year_start']}-{meta['year_end']}_{sid}.zip"

        if not force and prior and prior.get("dataset_hash") == meta["dataset_hash"] \
                and zip_path.exists():
            return {"session_id": sid, "skipped": True, "path": zip_path,
                    "name": meta["session_name"]}

        data = self._call("getDataset", id=meta["session_id"], access_key=meta["access_key"])
        blob = base64.b64decode(data["dataset"]["zip"])

        # Write to a temp name first so an interrupted download cannot look complete.
        tmp = zip_path.with_suffix(".zip.partial")
        tmp.write_bytes(blob)
        tmp.replace(zip_path)

        index[sid] = {
            "session_id": meta["session_id"],
            "session_name": meta["session_name"],
            "year_start": meta["year_start"],
            "year_end": meta["year_end"],
            "dataset_hash": meta["dataset_hash"],
            "dataset_date": meta.get("dataset_date"),
            "file": zip_path.name,
            "bytes": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "downloaded_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._index_path().write_text(json.dumps(index, indent=2, sort_keys=True))
        return {"session_id": sid, "skipped": False, "path": zip_path,
                "bytes": len(blob), "name": meta["session_name"]}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="show available Tennessee sessions (1 API call)")
    f = sub.add_parser("fetch", help="download session archives")
    f.add_argument("--from-year", type=int, default=2019,
                   help="earliest session end year to fetch (default 2019)")
    f.add_argument("--force", action="store_true", help="re-download even if unchanged")
    f.add_argument("--max-calls", type=int, default=MAX_CALLS_PER_RUN)
    args = p.parse_args(argv)

    client = LegiScanClient(max_calls=getattr(args, "max_calls", MAX_CALLS_PER_RUN))
    sets = sorted(client.dataset_list(), key=lambda s: s["year_start"])

    if args.cmd == "list":
        print(f"\n  {'SESSION':<40} {'YEARS':<12} {'SIZE':>9}  HASH")
        for s in sets:
            print(f"  {s['session_name'][:39]:<40} {s['year_start']}-{s['year_end']:<7}"
                  f"{s['dataset_size']/1048576:>7.1f}MB  {s['dataset_hash'][:12]}")
        return 0

    wanted = [s for s in sets if s["year_end"] >= args.from_year]
    log(f"sessions to consider: {len(wanted)} (ending {args.from_year} or later)")

    fetched = skipped = total_bytes = 0
    for meta in wanted:
        log(f"{meta['session_name']} ({meta['year_start']}-{meta['year_end']}) ...")
        r = client.fetch_dataset(meta, force=args.force)
        if r["skipped"]:
            log("  unchanged since last download, skipping")
            skipped += 1
        else:
            log(f"  saved {r['bytes']/1048576:.1f} MB -> {r['path'].name}")
            fetched += 1
            total_bytes += r["bytes"]
            time.sleep(1)

    log(f"done: {fetched} downloaded, {skipped} unchanged, "
        f"{total_bytes/1048576:.1f} MB, {client.calls} API calls used")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
