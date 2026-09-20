# Is the scraper broken, or was it just a quiet week?

TREF is a state web application that can change without notice. This is how to tell
the difference between "Tennessee filed nothing" and "our scraper silently stopped
working" — a distinction that matters because silence looks identical either way, and
this data backs public claims about named officials.

## What the job already does for you

- **Any failure exits non-zero**, which makes GitHub email the repository owner. A job
  that fails quietly would be worse than no job.
- **`--expect-rows` turns "nothing changed" into a failure**, and is applied only to
  the deadline-window schedules, where new filings genuinely should exist.
- **Every run writes a summary** to the Actions run page: row counts before and after.
- **The client refuses to guess.** It raises rather than continuing if the CSV export
  link disappears, if a response is not CSV, or if a page repeats byte-for-byte
  (cursor not advancing — see D63).

## Symptoms and what they mean

| Symptom | Likely cause |
|---|---|
| `no CSV export link found` | TREF changed its results page markup. Re-check the selectors in `tref._parse_results()`. |
| `expected CSV, got Content-Type 'text/html'` | The export URL now returns a page — often a session or error page rather than a file. |
| `batch N is byte-identical to a page already downloaded` | The "More" cursor stopped advancing. Real loop, not a large year. |
| `exceeded 5000 pages` | Paging behaviour changed fundamentally. Investigate before raising the cap. |
| HTTP 500 from `cesearch.htm` | TREF-side error. Seen repeatedly for **2023 specifically** and it has not yet resolved; retry, and if it persists for one year only, suspect their data rather than our code. |
| Runs succeed but row counts never move outside February–April | Probably correct — the in-session contribution ban. See `filing_calendar.md`. |
| Runs succeed but row counts never move in **October–December** | Suspicious. That is peak fundraising season; investigate. |

## Monthly check, five minutes

1. **Actions tab** — did every scheduled run complete?
2. `SELECT source, search_type, data_year, status, rows_added, started_at FROM data_pulls ORDER BY started_at DESC LIMIT 10;`
3. Pick one legislator, compare their most recent contribution date in the database
   against their filings on apps.tn.gov/tncamp.
4. Check the review queues: new TREF filer names and new donors need categorising, or
   money silently stops being attributed. New members arrive every election.

## If the layout changed

The raw downloads are kept as workflow artifacts for 90 days, and **manifests with a
SHA-256 per file are committed to the repository permanently**. So even after
artifacts expire there is a durable record of exactly what was downloaded and when,
which is what makes a later dispute answerable.

Fix the selectors in `src/tn_accountability/tref.py`, re-run for the affected year
with `--force`, then `load_tref --replace` for that slice. Do not delete anything
under `data/raw/` — move failed attempts aside as in D64.
