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

## Governing principles

These are not preferences. They constrain every phase and must not be traded away for
convenience in a later one.

### 1. Universal, non-partisan coverage

**Every legislator gets the same treatment, of either party, whether or not anyone is
interested in them.** The site covers all members who served — currently 207 people
across the 111th to 114th General Assemblies, 136 of them in the current session.

Johnny Garrett is the initial *test case* because an existing workbook allows the
pipeline to be checked against independent work. He is **not** the subject of the
project. Any analysis, threshold, view or page that works only for Garrett, or that
would produce a different answer depending on party, is a defect.

Concretely, this means:
- Phase 4 matches **all** legislators to TREF records, not a chosen few.
- Phase 5 computes the chamber baseline across **every** member, and each member's
  position is expressed relative to that baseline rather than in isolation.
- Phase 8 publishes a profile page for **every** legislator, not only flagged ones.
- Phase 9 applies identical thresholds to everyone. No manual additions or removals
  from the review queue.
- Party is a displayed attribute, never an input to any threshold or ranking.

**Why it matters:** the project's only real defence against a charge of bias is that
the same method was applied to everyone and the method is published. Selective
coverage forfeits that defence permanently, and it cannot be repaired afterwards by
adding the missing people later.

### 2. Raw data is evidence

Nothing under `data/raw/` is modified, renamed, or deleted — see D2, D64. Every
published figure traces to a source file and line via `data_pull_id`.

### 3. Patterns, not accusations

Neutral language throughout (PLAN.md Phase 8). The site states what the records show
and links to them. It does not allege wrongdoing.

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
| D30 | 2026-09-13 | Ask **TREF directly** (registry.info@tn.gov) for a bulk extract, not just TAP. | TREF is the primary source and is current; TAP is a third-party copy that stops at 2023. A single extract may also expose fields the web export does not. Drafted in `docs/tref_bulk_request.md`. |
| D31 | 2026-09-13 | Neither bulk request blocks the scraper; all three run in parallel. | Phase 7 needs ongoing TREF ingest regardless, so the scraper is never wasted work. Agency requests can stall for weeks, and stopping the scraper to wait would risk losing that time for nothing. |
| D32 | 2026-09-13 | Backfill writes to `data/raw/tref/backfill/<type>/<year>/`, not a dated directory. | Resume needs a stable path. A year is complete when it holds `_manifest.json`; reruns skip it. Dated directories stay for Phase 7 incremental pulls, where "what arrived on this date" is the meaningful grouping. |
| D33 | 2026-09-13 | An interrupted year is discarded and re-fetched, not resumed mid-way. | TREF's paging cursor lives in a server-side session that cannot be re-entered. Downloads go to `<year>.partial/` and are renamed to `<year>/` only on success, so a completed year is never torn or overwritten. `.partial` directories are working state, not evidence — the never-delete-raw-data rule does not apply to them. |
| D34 | 2026-09-13 | The manifest records a SHA-256 per file. | Lets the evidence trail be re-verified later without re-downloading, and catches silent corruption. Verified working: 32/32 files matched on re-check. |
| D35 | 2026-09-13 | A failed year logs and continues rather than aborting the run. | An overnight backfill must not lose nine good hours to one bad year. Failures are listed at the end and rerunning the same command retries only those. |
| D36 | 2026-09-13 | **Supabase security confirmed safe by default:** RLS is enabled on all 14 tables with no policies (deny-all), and `anon` holds no SELECT/INSERT/UPDATE/DELETE. | Checked directly, not assumed. Means loaded data is unreadable through the public API until policies are deliberately added. **Phase 8 will have to add read policies** for the public site — that is intended, but it is the moment to get it right. |
| D37 | 2026-09-14 | Upgraded Supabase to **Pro** (8 GB). | User decision, made before the large load. Supersedes the wait-and-measure stance in D13. |
| D38 | 2026-09-14 | **Measured** storage: 17 MB for 26,765 expenditure rows = **~635 bytes/row** in Postgres including indexes. | Extrapolates to **~1.6 GB** for the full ~2.5M-row backfill — close to the earlier 1.2-1.5 GB estimate, comfortable in 8 GB, impossible in 500 MB. This is measured, not estimated; prefer it. |
| D39 | 2026-09-14 | Migrations 0002/0003 add the TREF columns the Phase 1 schema had no home for. | The initial schema was written from PLAN.md's *description* of the data. Real files carry Type, Adj, Election Year, Candidate For, S/O and Description with nowhere to go. Loading would have silently dropped published fields, breaking the keep-raw rule. The loader now refuses to run if a source column is unmapped rather than discarding it. |
| D40 | 2026-09-14 | Migration 0004 drops NOT NULL from the raw counterparty-name columns. | Real filings omit them: a 2026 John Rose filing reports **$11,000 for "PROFESSIONAL SERVICES" with no vendor named** (3 such rows in 2026 alone). A placeholder would fabricate data. **Analysis views must treat a missing counterparty as a real category**, not assume it away — an unnamed payee is itself worth counting. |
| D41 | 2026-09-14 | Unparseable source values are kept raw with the cleaned column left null; the parser never guesses. | A 2026 filing by CONCERNED CONSTITUTIONAL CONSERVATIVES PAC is dated **02/29/2026 — a date that does not exist** (2026 is not a leap year). `expenditure_date_raw` preserves it, `expenditure_date` is null. Validates the raw-alongside-cleaned design on real data. |
| D42 | 2026-09-14 | Loading works on whole `(search_type, year)` slices, tracked in `data_pulls`. | TREF rows carry no stable record id, so row-level dedupe is unsafe — two identical legitimate contributions would be wrongly collapsed. Slice-level tracking makes reloads idempotent and explicit (`--replace`). Verified: a second load skipped and the row count held at 26,765. |
| D43 | 2026-09-14 | Backfill scope is **2019-2026**, not back to 2002. | Aligns with PLAN.md Phase 3, which starts bills at the 111th General Assembly (2019); campaign finance with no matching legislative record cannot be joined against anything yet. Extending backward to 2002 is explicitly a Phase 10 task and the backfill is resumable, so nothing is foreclosed. |
| D44 | 2026-09-14 | LegiScan **free Public API** is sufficient; no paid tier needed. | 30,000 queries/month. Phase 3's full backfill uses `getDatasetList` + `getDataset` (one call returns an entire session's bills, people, sponsorships and roll calls as a base64 ZIP) — roughly 10-20 Tennessee sessions since the 111th GA, so **under 25 calls total**. Phase 7 uses `getMasterListRaw` change hashes to fetch only bills that actually moved: well under 6,000 calls in a busy session month. Per-bill `getBill` calls would be ~8,000 for the same backfill — avoid. |
| D45 | 2026-09-14 | **LegiScan data is CC BY 4.0 — attribution is required, not optional.** | Every page presenting LegiScan-derived data (bills, sponsorships, votes) must visibly credit LegiScan and link the CC BY 4.0 licence, and the methodology page must state it. This is a licence obligation, not a courtesy. Build it into the Phase 8 templates from the start rather than retrofitting. |
| D46 | 2026-09-19 | Secrets move to the **macOS Keychain**, via the `keyring` library, with `.env` kept as a fallback. | `config.require()` reads the environment first, then the Keychain, so CI and one-off overrides still work. `.env` at chmod 600 on a FileVault disk was already reasonable; the Keychain removes the plaintext-at-rest copy and the risk of it being swept into a zip, backup, or screenshot. |
| D47 | 2026-09-19 | Use the `keyring` API, **never** the `security` CLI, to write secrets. | `security -w` reading from stdin **silently truncates at 128 characters** — `DATABASE_URL` is 149, so it would have stored a broken value that failed later looking like a credentials problem. Passing the value as an argument avoids truncation but exposes it in `ps`. The API has neither flaw. `put()` always reads back and compares. |
| D48 | 2026-09-19 | Keychain items created by the `security` CLI cannot be modified by Python (error -25244). | Their ACL trusts only `/usr/bin/security`. If a stale CLI-created item ever blocks a write, delete it with `security delete-generic-password -s tn-accountability -a <NAME>` and let `keyring` recreate it. |
| D49 | 2026-09-19 | Backfill completed **12 of 15 slices**: 1,240,545 rows, 218.6 MB. Three contribution years failed and are **still missing**. | 2020 (`IncompleteRead` mid-download), 2023 (exceeded the 500-page guard — the 'More' button never cleared), 2024 (HTTP 500 from TREF). All expenditure years 2019-2026 succeeded. Failed years left `.partial` directories, which the resume logic correctly ignores. |
| D50 | 2026-09-20 | Phase 3 loaded: 38,613 bills, 134,030 sponsorships, 48,490 roll calls, **2,472,724 votes**, 564 people. 5 API calls. | Database now 437 MB. LegiScan `change_hash` stored per bill for Phase 7 incremental updates. |
| D51 | 2026-09-20 | LegiScan publishes vote text as both `NV` and `Not Voting`; only the long form was mapped, so 18,201 votes landed as `other`. Corrected. | The loader reports unmapped values at the end of every run — that report is what caught it. **Keep that behaviour**: a silently mislabelled vote corrupts analysis invisibly. |
| D52 | 2026-09-20 | Membership counts are 101 House / 35 Senate for the 114th, not the 99/33 PLAN.md expects. **Not a bug.** | Terms are derived from "appears in the General Assembly", which includes members who resigned mid-term plus their special-election replacements. PLAN.md's check assumes *current* membership; Phase 3 explicitly asked for everyone who served. |
| D53 | 2026-09-20 | **OPEN:** Garrett has 28 primary-sponsored bills in the 114th; PLAN.md's workbook says 50. | An earlier figure of 206 was my SQL bug — a `general_assembly` filter placed in a `LEFT JOIN` condition, which does not restrict rows. 28 is the corrected count (plus 3 joint and 2 simple resolutions). The 28-vs-50 gap is unexplained and must be resolved against the workbook before Phase 5 calibration. |
| D54 | 2026-09-20 | **RLS does not restrict TRUNCATE**, and Supabase granted it to `anon`/`authenticated` on every table, with a default ACL that re-granted it on each new table. Revoked in migration 0006. | Not reachable today (anon cannot log in; PostgREST exposes no TRUNCATE) but becomes reachable with the first anon-callable function, which Phases 8-9 likely add. Verified fixed, including a probe confirming new tables no longer inherit it. |
| D55 | 2026-09-20 | RLS is on with **zero policies** = deny-all, so the Phase 8 site will read nothing until read access is granted deliberately. | Correct default. Grant `SELECT` on purpose-built views only, with an explicit anon policy — and never by loosening 0006. `legislator_tref_ids` must not expose `approved=false` rows as if confirmed. See `docs/security_audit.md`. |
| D56 | 2026-09-20 | Disaster recovery rests on `data/raw/` + migrations + loaders, not on database backups. | The database is fully reproducible from the raw files without contacting any agency. That makes an off-machine backup of `data/raw/` more valuable than PITR. |
| D57 | 2026-09-20 | **Upgrading to Pro did not resize the disk.** The project is on ~1.8 GB, not 8 GB. | Supabase auto-scales disk gradually with a cooldown; the plan's 8 GB is an allowance, not an immediate allocation. 750 MB of data + 1 GB of WAL filled it, and **Supabase put the database into read-only mode** (`default_transaction_read_only=on`) to protect it. **Action required: Project Settings -> Compute and Disk -> Disk size -> 8 GB.** |
| D58 | 2026-09-20 | When the disk fills, a session can temporarily override read-only with `SET default_transaction_read_only = off` to free space. | This is how the oversized indexes were dropped while the database was locked. Supabase clears the flag on its own once there is headroom. Use only to free space, never to keep writing into a full disk. |
| D59 | 2026-09-20 | Dropped the per-row unique indexes on `(source_file, source_record_id)` — migration 0007. | 111 MB at only 371k rows, versus 3-10 MB for every other index, because it was a unique index over two text columns with a ~70-character path repeated per row. It was also **redundant**: slice-level tracking (D42) plus single-transaction loads already prevent the duplicate it guarded against. The columns remain, so provenance is untouched. |
| D60 | 2026-09-20 | Measured: contributions cost **624 bytes/row** including indexes. | Full 2019-2026 contributions ~1.0 GB; whole database ~1.4 GB at completion, ~2.5 GB working with WAL. Confirms 8 GB is right and 500 MB was never viable. |
| D61 | 2026-09-20 | Supabase auto-expanded the disk **2 GB -> 8 GB**, confirming D57. | Pro auto-scales at 90% usage, +50% per expansion, **max 4 disk modifications per rolling 24 hours**. That limit is why a single jump to 8 GB was preferable to incremental nudges. |
| D62 | 2026-09-20 | **RESOLVED — the Garrett discrepancy is not ours.** capitol.tn.gov shows exactly **28** House bills for Rep. Garrett in the 114th GA, with the same bill numbers in the same order as our database (HB0032, HB0170, HB0645, HB0817, HB0818, HB0819...). | Verified against the Tennessee General Assembly's own sponsor list at `wapp.capitol.tn.gov/apps/LegislatorInfo/SponsorList?district=H450&ga=114`. **This inverts PLAN.md Phase 5's assumption**, which treats the workbook as ground truth and says to explain our differences. Here the pipeline agrees with the authoritative source and the workbook's 50 is the number needing explanation. Do not "fix" the pipeline to match the workbook. |
| D63 | 2026-09-20 | Replaced the fixed 500-page scraper cap with **content-hash loop detection**. | 2023 tripped the cap with 500 *distinct* pages — TREF served ~346 rows/page that year versus ~800-890 for others, so a normal year looked like a runaway. A page count cannot tell a large year from an infinite loop; a byte-identical repeat can. Cap raised to 5000 as a last resort only. |
| D64 | 2026-09-20 | Failed `.partial` download directories are **moved to `data/raw/_failed_attempts/<timestamp>/`**, never deleted. | Consistent with the never-delete-raw-data rule. They are also evidence of what the site returned during a failure, which matters if TREF's behaviour is ever questioned. |
| D65 | 2026-09-20 | **Universal non-partisan coverage is a governing principle**, recorded in its own section above rather than as a decision row. | User's explicit direction: Garrett is the initial test case, not the focus; the site must cover all active and recent legislators of both parties equally. Verified the database already supports it: 207 people across the 111th-114th GAs (R, D and one I), 136 currently serving. Any view, threshold or page that works only for one person or differs by party is a defect. |
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
2. **Phase 2 — collection solved, loading not started.** The backfill CLI works
   (`python -m tn_accountability.backfill --years 2019-2026`). Verified end to end on
   expenditures 2026: 26,765 rows, 32 batches, 3.8 MB, 215s, all checksums matching,
   and a rerun correctly skipped the completed year.
   The loader is built and verified: `python -m tn_accountability.load_tref --years 2026`
   loaded 26,765 rows in 3 seconds via COPY, matching the manifest exactly, with 100%
   provenance and 100% amount parsing.
3. Send the two bulk requests (`docs/tref_bulk_request.md`, `docs/tap_bulk_request.md`).
4. **Backfill 2019-2026 is RUNNING** (started 2026-09-14 09:02, detached via nohup,
   PID in `data/raw/tref/backfill.pid`, log at `data/raw/tref/backfill.log`).
   15 slices: contributions 2019-2026 + expenditures 2019-2025. Expect several hours.
   Check with `tail -f data/raw/tref/backfill.log`. It is resumable — rerunning the
   same command picks up whatever did not finish.
5. When it finishes: `python -m tn_accountability.load_tref --years 2019-2026`, then
   Phase 3 (LegiScan bills/sponsors/votes) — needs `LEGISCAN_API_KEY`, still missing.


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
