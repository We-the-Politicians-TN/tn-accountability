# STATUS — project state and decision record

**Purpose.** This file is the durable memory of the project. Claude Code's context
window gets truncated between and within sessions; this file is what survives.
It records *decisions and why they were made*, not just tasks completed, so that
any future session can reconstruct the reasoning without replaying the history.

**Every session:** read `PLAN.md` and this file before doing anything. At the end,
append to the Session log and add any new entries to Decisions.

---

## Current phase

**Phase 0 — complete locally**, GitHub push pending (see Blockers).
**Phase 1 — schema written, NOT applied.** Blocked on `DATABASE_URL`.

---

## Decisions

Append-only. Newest at the bottom. Never delete an entry — if a decision is
reversed, add a new entry that says so and why.

| # | Date | Decision | Why |
|---|---|---|---|
| D1 | 2026-09-13 | Repo is public from day one. | Open methodology is the defense against claims of bias (PLAN.md Phase 10). |
| D2 | 2026-09-13 | `data/raw/**` is gitignored; directory structure preserved with `.gitkeep`. | Raw files are the evidence trail and must stay byte-identical, but the Accountability Project TN files are ~2M rows — too large for git. They live on disk and in backups, not in the repo. |
| D3 | 2026-09-13 | Default branch is `main`. | Matches GitHub default; avoids a rename later. |
| D4 | 2026-09-13 | Scaffolded on system Python 3.9.6. | Only Python on the machine; no Homebrew installed. Works for current deps (pandas 2.3.3, psycopg 3.2.13 all installed cleanly). **Revisit before Phase 7** — 3.9 is EOL as of Oct 2025 and Playwright/newer pandas will eventually require 3.11+. Swapping the venv is a one-command change. |
| D5 | 2026-09-13 | Secrets live only in `.env`, loaded via `python-dotenv`; `.env.example` documents every variable. | Keeps credentials out of a public repo. CI (Phase 7) will supply the same names as GitHub Actions secrets; Cloudflare (Phase 8) as environment variables. |
| D6 | 2026-09-13 | `DATABASE_URL` uses Supabase's session pooler (port 5432), not the direct connection. | Direct connections are IPv6-only on Supabase free tier; the pooler works from GitHub Actions runners and most home networks. |
| D7 | 2026-09-13 | Terms and TREF candidate IDs are separate tables (`legislator_terms`, `legislator_tref_ids`), not columns on `legislators`. | PLAN.md asks for "terms served with start/end dates" and "TREF candidate IDs — a legislator can have several". Both are one-to-many. |
| D8 | 2026-09-13 | `legislator_tref_ids.approved` defaults to false; analysis views must filter on it. | Phase 4 requires human sign-off on matches below 90% confidence. Enforcing it in the schema means an unapproved guess cannot silently reach a published figure. |
| D9 | 2026-09-13 | Roll calls split into `roll_calls` (the vote event, with totals) + `votes` (per-legislator). | PLAN.md says `votes` (bill, roll call, legislator, vote cast). A roll call has its own date, chamber, and tallies that would otherwise repeat on every vote row. |
| D10 | 2026-09-13 | `contribution_date_raw` and `amount_raw` are `text`, kept alongside parsed values. | A source value that fails to parse is preserved as evidence rather than dropped. Applies the PLAN.md rule that every table keeps raw alongside cleaned. |
| D11 | 2026-09-13 | Partial unique index on `(source_file, source_record_id)` for contributions and expenditures. | Makes re-ingest idempotent for rows that carry a source identifier. Rows without one still need application-level dedupe — open risk for Phase 7. |
| D12 | 2026-09-13 | Migrations are append-only, tracked in `schema_migrations` with a SHA-256 of each file. | An applied migration that gets edited is a silent drift bug; the runner refuses to continue if a hash changes. |

---

## Environment facts

Things discovered about this machine/accounts that are expensive to rediscover.

- Python: system `python3` 3.9.6 at `/usr/bin/python3`. No Homebrew, no pyenv.
- Node: v24.19.0, npm 11.17.0. Adequate for Evidence (Phase 8).
- Git: 2.50.1. Identity configured as Timothy King <wayfarerinteractivellc@gmail.com>.
- **`gh` CLI is NOT installed** — GitHub repo creation and push must be done manually
  or after installing `gh`. See Blockers.
- Virtualenv at `.venv/`. Activate with `source .venv/bin/activate`.

---

## Accounts / credentials status

| Service | Account created | Credential in `.env` | Notes |
|---|---|---|---|
| GitHub | ? | n/a | Repo `tn-accountability` not yet created |
| Supabase | ? | ❌ | Need `DATABASE_URL` before Phase 1 can run |
| LegiScan | ? | ❌ | Need `LEGISCAN_API_KEY` before Phase 3 |
| Accountability Project | ? | n/a | MuckRock login; manual download in Phase 2 |
| Cloudflare | ? | ❌ | Not needed until Phase 8 |

---

## Verified by a human

Nothing yet. Phase 0 verification steps are in `PLAN.md` line 31.

---

## Next

1. Create the public GitHub repo `tn-accountability` and push (see Blockers).
2. Confirm Phase 0 verification: repo visible on GitHub, `.env` absent from it.
3. Apply the Phase 1 migration once `DATABASE_URL` is in `.env`:
   `source .venv/bin/activate && PYTHONPATH=src python -m tn_accountability.migrate`
   **The SQL has never been executed** — expect to fix syntax errors on first run.
4. Verify in Supabase Table Editor that all tables exist, then Phase 2 backfill.

---

## Blockers

- **`gh` CLI not installed**, so the repo cannot be created from this machine
  programmatically. Either install it (`brew install gh`, which first needs
  Homebrew) or create the repo in the GitHub web UI and run:
  ```
  git remote add origin https://github.com/<user>/tn-accountability.git
  git push -u origin main
  ```
- **No Supabase `DATABASE_URL`.** Phase 1's migration is written but **not applied
  and not validated** — there is no Postgres on this machine (no psql, no Docker),
  so the SQL has never been parsed by a database. First apply may surface errors.
- **No `LEGISCAN_API_KEY`.** Required for Phase 3.

---

## Session log

Newest first. One entry per session.

### 2026-09-13 — Phase 0 scaffold + Phase 1 schema (unapplied)

- Created directory structure, `git init` on `main`.
- Wrote `.gitignore` (secrets + large data excluded), `.env.example`, `README.md`,
  `PLAN.md` (full build plan), `STATUS.md`, `requirements.txt`.
- Created `.venv` on Python 3.9.6 and installed dependencies.
- **Verified:** `git check-ignore .env` confirms `.env` is ignored; `git status`
  shows no data or secret files staged.
- Wrote `sql/migrations/0001_initial_schema.sql` (13 tables, 5 enum types),
  `src/tn_accountability/migrate.py` (migration runner), and `docs/schema.md`
  (plain-English description of how the tables connect).
- **Not verified:** nothing pushed to GitHub (`gh` missing); the migration SQL has
  never been run against any Postgres instance.
- **Next:** push to GitHub; get `DATABASE_URL`; apply the migration.
