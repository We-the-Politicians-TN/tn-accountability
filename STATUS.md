# STATUS — project state and decision record

**Purpose.** This file is the durable memory of the project. Claude Code's context
window gets truncated between and within sessions; this file is what survives.
It records *decisions and why they were made*, not just tasks completed, so that
any future session can reconstruct the reasoning without replaying the history.

**Every session:** read `PLAN.md` and this file before doing anything. At the end,
append to the Session log and add any new entries to Decisions.

---

## Current phase

**Phase 0 — COMPLETE and verified.** Repo public at
https://github.com/We-the-Politicians-TN/tn-accountability, `.env` confirmed absent.
**Phase 1 — COMPLETE.** Schema applied to Supabase and functionally verified.
Next: Phase 2 historical backfill.

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
| D13 | 2026-09-13 | Start Supabase on the Free plan despite knowing it is too small for the full Phase 2 backfill. | Free gives 500 MB (verified on supabase.com/pricing). Estimated need is 1.2-1.5 GB for ~2.0M contributions + ~480K expenditures with raw+normalized columns and six indexes on `contributions` — roughly 3x over. But Free costs nothing, Phase 1 fits, and Phase 2 will produce a real bytes-per-row measurement. Upgrade to Pro ($25/mo, 8 GB, then $0.125/GB) when measured, not on an estimate. **Before upgrading, ask Supabase about nonprofit/open-source credits** — the repo is public and the org is a civic project. |
| D14 | 2026-09-13 | Supabase org named "We the Politicians TN", type Personal. | Matches the GitHub account `We-the-Politicians-TN`. Supabase's org "type" is segmentation metadata only — it does not affect features or billing — so it is not worth agonizing over and is changeable later. |
| D15 | 2026-09-13 | Push over SSH with a dedicated passphrase-less key `~/.ssh/id_ed25519_github`, pinned in `~/.ssh/config` with `IdentitiesOnly yes`. | The pre-existing `~/.ssh/id_ed25519` is passphrase-protected and its passphrase is not recoverable, so it cannot sign unattended — GitHub accepted the key but SSH could not use it. A separate key leaves the original untouched for other hosts. `IdentitiesOnly yes` stops SSH offering the old key first. |
| D16 | 2026-09-13 | Commits are authored as `We the Politicians TN <42594056+We-the-Politicians-TN@users.noreply.github.com>`, set per-repo. | Commit history on a public repo about named politicians is permanently public and scraped; the maintainer's personal email should not be in it. The three pre-push commits were rewritten with `filter-branch` and the `refs/original/` backups deleted, so no personal address is reachable. |
| D17 | 2026-09-13 | GitHub account `Wayfarerint-coder` is NOT used for this project. | User's explicit instruction. Its credential still sits in the macOS keychain for github.com; the SSH config bypasses it entirely. |
| D18 | 2026-09-13 | `DATABASE_URL` must use the **session pooler**, never the direct connection. | Verified empirically: `db.zrtmstikjixpuqtorhfj.supabase.co` has an AAAA record and **no A record**, and connecting failed with "failed to resolve host". The pooler host `aws-0-us-east-1.pooler.supabase.com` resolves to IPv4 and connects. Same constraint will apply to GitHub Actions runners in Phase 7. |
| D19 | 2026-09-13 | The database password contains characters that must be percent-encoded in the URL (it has an `@`). | An unencoded `@` makes `urlparse` read the password as the hostname. If the password is ever rotated, re-encode it — `urllib.parse.quote(pwd, safe='')`. Encoding expanded 38 chars to 56. |
| D20 | 2026-09-13 | **PLAN.md Phase 2 as written is not achievable.** The Accountability Project caps downloads at 10,000 rows. | Verified on publicaccountability.org/search-guide/: "Downloads are capped at 10,000 rows. If you are looking for more data than this, please contact us." The TN contributions dataset is 2,027,069 rows — the cap is 0.5% of it. There is no bulk download button on the dataset page; the only download is on the Dataset Search page and is subject to the cap. Bulk access requires contacting them. |
| D21 | 2026-09-13 | TAP's own data is stale: TN contributions cover **2002–2023**, expenditures **2004–2023**. | It is 2026. Even a successful bulk request from TAP leaves a ~3-year gap that must be filled from TREF regardless. |
| D22 | 2026-09-13 | TAP built their TN dataset by scraping TREF directly — their script is a working blueprint. | `state/tn/contribs/docs/get_tn_contribs.R` in irworkshop/accountability_datacleaning POSTs to `https://apps.tn.gov/tncamp-app/public/cesearch.htm` per year, reads the CSV link from `ceresults.htm`, and pages via `ceresultsnext.htm`. This means PLAN.md Phase 2 (bulk download) and Phase 7 (TREF scraper) are really the same piece of work, and the primary source has no row cap and is current. |
| D24 | 2026-09-13 | Phase 2 pivots to scraping TREF directly; the TAP request goes out in parallel but nothing waits on it. | User decision. TREF is the primary source, has no row cap, and is current — TAP's copy stops at 2023. The scraper is required for Phase 7 anyway, so this is not extra work, it is the same work done earlier. |
| D25 | 2026-09-13 | **The TREF app moved from `/tncamp-app/` to `/tncamp/`.** | `https://apps.tn.gov/tncamp-app/public/cesearch.htm` now 302-redirects. TAP's `get_tn_contribs.R` would silently fail against the old path. All form field names are unchanged, so only the base URL needed updating. |
| D26 | 2026-09-13 | Parse results from the POST response directly; skip the separate `GET ceresults.htm`. | The POST redirects to `ceresults.htm`, so its body already *is* batch 1. The extra GET was a wasted request and was where the intermittent TLS failures kept landing. |
| D27 | 2026-09-13 | The CSV export returns the **entire current batch**, not the 50 rows displayed. | Verified: a page reading "754 results found, displaying 1 to 50" exported 755 lines. Batch sizes vary (~750-810 observed), so row totals must be counted from the files, never taken from the page banner. |
| D28 | 2026-09-13 | Every TREF request is wrapped in retry-with-backoff. | `apps.tn.gov` intermittently drops TLS handshakes (`SSLEOFError: EOF occurred in violation of protocol`). Five consecutive CSV fetches then succeeded, so it is transient — but across a backfill of thousands of requests it is a certainty. Aggravated by system Python 3.9 linking **LibreSSL 2.8.3**; see D4. |
| D29 | 2026-09-13 | Measured TREF throughput: **~6 batches/min, ~4,500 rows/min**, ~190 bytes per CSV row. | Implies roughly **9-10 hours of continuous scraping** for the full ~2.5M-row backfill, and ~475 MB of raw CSV on disk. The backfill must be resumable and run unattended; it cannot be a single foreground session. |
| D23 | 2026-09-13 | `.env` is `chmod 600`. | Was `644`, world-readable on a multi-user machine. Disk is FileVault-encrypted and the project is not in a cloud-synced folder, so this closes the remaining local exposure. |

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
| GitHub | ✅ | n/a | https://github.com/We-the-Politicians-TN/tn-accountability — public, pushed, verified. Account is a personal account, not an org. |
| Supabase | ✅ | ✅ | Project ref `zrtmstikjixpuqtorhfj`, region us-east-1, PostgreSQL 17.6, Free plan. Connects via session pooler. Free tier will not hold Phase 2 — see D13. |
| LegiScan | ? | ❌ | Need `LEGISCAN_API_KEY` before Phase 3 |
| Accountability Project | ? | n/a | MuckRock login; manual download in Phase 2 |
| Cloudflare | ? | ❌ | Not needed until Phase 8 |

---

## Verified by a human

- **Phase 0 (PLAN.md line 31):** repo is public on GitHub with the expected files;
  `.env` returns 404 on the GitHub API, confirming it was never pushed; `.gitignore`
  lists `.env`. Verified 2026-09-13.
- **Phase 1 (PLAN.md line 39):** schema applied to Supabase. Queried the live database:
  13 project tables + `schema_migrations`, 5 enum types, 52 indexes, 25 foreign keys,
  8 triggers. Functional test confirmed the legislator↔contribution join works, that a
  contribution without `data_pull_id` is rejected, that a term ending before it starts
  is rejected, and that `legislator_tref_ids.approved` defaults to false. Test rolled
  back; database left empty. **Still to do by a human:** eyeball the tables in the
  Supabase Table Editor.

---

## Next

1. Look at the tables in the Supabase Table Editor to close out Phase 1 verification.
2. **Phase 2 — BLOCKED as written.** The TAP download cap (D20) means the files
   PLAN.md assumes cannot be obtained that way. Decision pending: request bulk access
   from TAP, scrape TREF directly (D22), or both.
3. Expect the Free tier's 500 MB limit to bite during Phase 2 (D13). Measure actual
   bytes/row on a partial load before deciding whether to upgrade.

---

## Blockers

- **RESOLVED** — GitHub push. See D15/D16.
- **RESOLVED** — Supabase connection. See D18/D19.
- **Supabase Free tier is ~3x too small for Phase 2.** Not blocking yet; see D13.
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
- **Next:** resolve the GitHub push permission; get `DATABASE_URL`; apply the migration.

### 2026-09-13 (later still) — Phase 1 applied and verified

- Diagnosed two problems with the pasted connection string: the password contains an
  `@` (broke URL parsing) and the string was the direct connection, which is IPv6-only
  and unreachable from this network. Percent-encoded the password in place and rewrote
  the URL to the session pooler. See D18/D19.
- Applied `0001_initial_schema.sql` — succeeded on the first run, no syntax errors.
- **Verified against the live database**, not just the runner's exit code: table/column
  counts, enum values, index/FK/trigger counts, and a functional insert-join-rollback
  test exercising the NOT NULL provenance constraint, the term date check, and the
  `approved` default.
- **Next:** Phase 2 backfill — blocked on the manual Accountability Project download.

### 2026-09-13 (later) — GitHub auth resolved, Phase 0 pushed and verified

- Push initially denied: keychain credential was `Wayfarerint-coder` (not used, per D17).
- Switched `origin` to SSH. First key failed because it is passphrase-protected and
  the agent was empty — GitHub logged "Server accepts key" then "No more authentication
  methods to try". Generated `~/.ssh/id_ed25519_github` without a passphrase (D15).
- Consolidated `~/.ssh/config`, which had accumulated three conflicting `Host github.com`
  blocks; SSH is first-match-wins so the old key was still winning. Backup at
  `~/.ssh/config.bak-*`.
- Rewrote the three commits to the noreply identity and deleted `refs/original/` (D16).
- Pushed. **Verified:** repo public, expected files present, `.env` returns 404.
- Verified Supabase Free vs Pro limits against supabase.com/pricing (D13/D14).
