# Tennessee campaign finance filing calendar

Drives the cadence in `.github/workflows/ingest-tref.yml`: weekly normally, daily
through the fortnight around each deadline, when new filings actually appear.

## ⚠ These dates are UNVERIFIED — confirm before relying on them

I could not find a published deadline calendar on tn.gov/tref, and I am not willing to
assert statutory dates I have not checked. The dates below are what I believe the
schedule to be; **treat them as a starting point, not a source.**

Confirm with the Registry directly — registry.info@tn.gov, (615) 741-7959 — or in
TCA Title 2, Chapter 10. It is a reasonable thing to ask in the same call as the bulk
data request in `tref_bulk_request.md`.

**The consequence of these being wrong is small.** The weekly run catches any filing
within seven days regardless; the deadline windows only make the data fresher during
busy periods. A wrong date costs timeliness, never completeness.

## Believed schedule for state candidates and PACs

| Report | Believed due date | Covers |
|---|---|---|
| Year-end / annual | January 31 | Jul 1 – Dec 31 |
| First quarter | April 10 | Jan 1 – Mar 31 |
| Second quarter | July 15 | Apr 1 – Jun 30 |
| Third quarter | October 10 | Jul 1 – Sep 30 |
| Pre-primary | ~7 days before a primary | through ~10 days before |
| Pre-general | ~7 days before a general | through ~10 days before |

Election-year reporting is heavier than the above; in a general election year expect
additional pre-election reports. **Add the specific pre-primary and pre-general dates
to the workflow cron in an election year** — they are the filings most worth having
promptly, and the standing quarterly windows will not cover them.

## Why the in-session ban matters to the schedule

Tennessee bars contributions while the General Assembly is in session. Measured in the
2025 data: January $1,385,084, **February $1,700**, March $2,498 (see
`methodology_findings.md`). So February through April genuinely produces almost no new
contribution activity.

**A quiet run in those months is normal and must not be read as breakage.** This is
exactly why `--expect-rows` is applied only to the deadline windows.
