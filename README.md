# Tennessee Legislator Accountability Platform

A public, reproducible record of Tennessee state legislators: who funds them, what
they sponsor, and how those two things line up in time and subject matter.

Every number on the public site traces back to a primary source — a TREF campaign
finance filing, a LegiScan bill record, or a Tennessee Ethics Commission
registration. The methodology is published alongside the findings so anyone can
check the work.

## What this is not

This project does not allege wrongdoing. It surfaces **patterns for review** with
the underlying records attached. Tennessee bans contributions during session, so
nearly every legislator's fundraising clusters in the same pre-session months —
timing alone is not evidence of anything. The primary signal is *subject-matched*:
contributions from donors in the same industry as a bill the legislator sponsored.

## Data sources

| Source | What it provides | Access |
|---|---|---|
| [LegiScan](https://legiscan.com) | Bills, sponsorships, roll-call votes, legislator records | Free API key |
| [The Accountability Project](https://publicaccountability.org) | Historical TN contributions and expenditures (back to 2002) | MuckRock login |
| [TREF](https://apps.tn.gov/tncamp) | Ongoing TN campaign finance filings | Public site, scraped |
| [TN Ethics Commission](https://www.tn.gov/ethics) | Lobbyist and lobbyist-employer registrations | Public downloads |

## Layout

```
data/raw/          Downloaded source files, never modified. The evidence trail.
data/processed/    Derived/cleaned artifacts. Regenerable from raw.
sql/migrations/    Schema migrations, applied in filename order.
src/tn_accountability/
                   Ingest, matching, and analysis code.
docs/              Methodology notes, data dictionary, filing calendar.
tests/             Tests.
PLAN.md            The full build plan, phase by phase.
STATUS.md          Running log: done / verified / next. Read before working.
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in real values
```

`.env` holds every secret and is gitignored. Never commit it.

## Ground rules

- **Never modify or delete anything in `data/raw/`.** Those files are the evidence
  trail; reproducibility depends on them being byte-identical to what was published.
- Every table keeps the raw source text alongside any cleaned version.
- Every ingest run is logged in the `data_pulls` table.
- The repo and the cleaned data stay public. Open methodology is the defense
  against claims of bias.

## Status

Early build. See [STATUS.md](STATUS.md) for where things actually stand and
[PLAN.md](PLAN.md) for the phases ahead.
