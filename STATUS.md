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

### 4. Every disclosed channel of influence, side by side (added 2026-09-21)

The user's stated goal: capture **any method by which a legislator can receive money,
benefits or items** — contributions, sponsored events, meals, travel, outside income,
directorships, retainers — so the public sees the full picture of where influence
could enter, and legislators are accountable to voters rather than to money.

Two things this does and does not mean. It means every *disclosed* channel is shown
together on a member's page. It does not mean inferring that any of it changed a vote:
motive is never in the data, and principle 3 stands. Tennessee's gift ban (TCA
§ 3-6-305) also means the individual "free lunch" is largely illegal rather than merely
hidden; what is lawful is group events and it is reported. See
`docs/influence_channels.md`.

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
| D66 | 2026-09-20 | **TREF publishes no district or office** alongside recipient names, so Phase 4 matching is name-only. | PLAN.md assumed "name matching plus district and office". `expenditures.candidate_for` looked promising but holds another person's name (and junk like `AAAAAA, AAA`), not an office. This makes ambiguity handling the whole game. |
| D67 | 2026-09-20 | **Match confidence measures ambiguity, not string similarity.** The score is discounted by how close the runner-up is, so a name matching two legislators equally well can never auto-approve. | Tennessee has three sitting Brookses, three Johnsons, three Joneses, and two simultaneous Hills. Raw similarity alone would auto-approve a coin-flip. Thresholds: raw >= 92 **and** margin >= 15 to auto-approve. |
| D68 | 2026-09-20 | Scoring weights the **surname at 65%**, and a surname mismatch caps the total at 60. | Whole-string similarity let a shared first name carry an unrelated surname: `LEE, BILL` (Governor Bill Lee, not a legislator) scored 57 against *Bill Beck*. TREF contains many non-legislators — governors, mayors, local candidates — and for those the correct output is no match, not a best guess. |
| D69 | 2026-09-20 | **`BARRETT` and `GARRETT` differ by one letter and both sit in the TREF data.** | `BARRETT, JOSEPH M.` scores 79 against Jody Barrett and 73 against Johnny Garrett — margin 6, so it is held for review rather than auto-applied. Without the ambiguity discount, Jody Barrett's $120,792 could have been attributed to the project's primary test subject. **Never lower the margin threshold.** |
| D70 | 2026-09-20 | `propose` now deletes superseded proposals (`approved_by IS NULL`) before writing. | The conflict key includes `legislator_id`, so re-running after a scoring change left the old wrong match in place beside the new one — one TREF name proposed against two legislators, which a later bulk approval could sweep in. Human approvals are preserved because they carry `approved_by`. |
| D71 | 2026-09-20 | **Joining contributions and sponsorships in one query fans out and inflates money totals.** | A verification query reported Garrett at **$70,642,550**; the real figure is **$342,925**, multiplied by his 206 sponsorship rows. Correct figure confirmed by computing aggregates in independent subqueries. **Every Phase 5 view and Phase 8 page must compute money and bill aggregates separately** — this bug class would put a fabricated eight-figure sum on a public page about a named official. |
| D72 | 2026-09-20 | Phase 4 result: 173 auto-approved, 70 pending review; 48,994 contributions and 67,732 expenditures linked. | $33.9M linked to legislators across both parties (R 130/157, D 42/49). Only 4.7% of all contributions link to a legislator, which is expected: most TREF money goes to PACs and non-legislative candidates. |
| D73 | 2026-09-20 | **The pre-introduction contribution total is a calendar artifact, not a signal.** | All 33 of Garrett's 114th-GA primary bills show nearly identical pre-90-day totals ($45,250, $45,250, $44,250, $42,900, $40,150 x5) because they are *the same contributions* counted against every bill — bills introduced weeks apart have almost entirely overlapping lookback windows sitting on the Oct-Jan fundraising peak. **Phase 9 must not rank the review queue on this measure**; it would surface whoever introduced bills nearest the fundraising peak and present a calendar artifact as a finding about a named person. See `docs/methodology_findings.md`. |
| D74 | 2026-09-20 | The in-session contribution ban is confirmed, and it is severe: **Jan 2025 $1,385,084 -> Feb $1,700 -> Mar $2,498**. | An ~800-fold drop when the General Assembly convenes. PLAN.md Phase 5 predicted this; the data is more extreme than expected. Confirms timing alone cannot distinguish anyone, and that Phase 6 subject matching is the primary signal. |
| D75 | 2026-09-20 | Baseline established: House median $258,832 (n=96), Senate median $569,306 (n=34). **Garrett is 1.81x his chamber median — above median but sharing that band with 14 others.** | On fundraising volume alone he is not an outlier. This is exactly why the baseline must exist before any figure is published. |
| D76 | 2026-09-20 | Party ratios differ (R mean 1.19, D mean 0.98) and **this should be published, not omitted**. | Republicans hold both majorities and the leadership positions that attract money. The method is party-blind and both extremes contain both parties (Sexton R 6.38x, Freeman D 3.92x at the top; Hardaway D 0.03x, Fritts R 0.18x at the bottom). Stating the difference and showing the method does not cause it is stronger than leaving a reader to wonder. |
| D77 | 2026-09-20 | **`passed_date` is present for only 3,958 of 5,925 passed 114th-GA bills**, so the post-passage measure returns zero for most. | Derived by scanning LegiScan history text for 'signed by governor' / 'public chapter', which misses other routes to passage. Must be improved before the post-passage measure is published. |
| D78 | 2026-09-20 | **36% of bills are ceremonial and must be excluded from every analysis.** `bills.is_ceremonial` flags 13,730 of 38,613. | Memorial resolutions honour retiring teachers and winning ball teams: no policy content, so pairing one with a donor's industry is meaningless and publishing such a pairing about a named legislator would be indefensible. Split is almost exactly by bill type — type B 0% ceremonial, JR 92%, R 95%. Also inflates apparent activity: chamber mean falls from 68.9 primary sponsorships to 43.0 substantive, and 75 of Garrett's 206 are memorials. |
| D79 | 2026-09-20 | Regex industry rules use **prefix matching (leading `\b` only)**. | The first version used `\bBANK\b`, whose trailing boundary cannot match "BANKERS". That silently dropped Tennessee Bankers Assn PAC, Tennessee Realtors PAC, Lawyers Involved for TN and others — categorised money rose from 20.2% to 37.9% on fixing it. Watch for this whenever a rule looks correct but matches nothing. |
| D80 | 2026-09-20 | Donor categorisation covers **56.5% of non-individual money**; $10.9M across 303 PACs remains uncategorised and is the review priority. | Individuals ($18.2M) legitimately have no industry — the employer field is 58% populated but dominated by RETIRED / SELF / NOT EMPLOYED, so it cannot rescue them. Non-individual coverage is the meaningful denominator for subject matching. |
| D81 | 2026-09-20 | **The subject-matched signal works and behaves as Phase 5 predicted.** | For Garrett's 114th-GA bills the unrestricted pre-introduction total is near-constant (45,250 / 42,900 / 40,150 x4 — the calendar) while the subject-matched figure varies $11,000 -> $0. `f_subject_matched()` keeps both columns side by side so the calendar effect stays visible rather than hidden. |
| D82 | 2026-09-20 | Domain **wethepoliticianstn.com** on Cloudflare; project email **wethepoliticianstn@gmail.com**. | Recorded for Phase 8 deployment and so outbound correspondence uses one address. |
| D83 | 2026-09-20 | **Phase 7 does NOT use Playwright**, contrary to PLAN.md. | The existing HTTP client hits the same TREF endpoints and is proven against 1.3M rows. Playwright would add ~300 MB of browser binaries to every CI run, slower execution and a new failure mode, to reach a site that requires no JavaScript. **Revisit only if TREF moves behind a JS-rendered interface** — then Playwright becomes necessary, not optional. |
| D84 | 2026-09-20 | **Zero rows is a failure when rows were expected** (`--expect-rows`), applied only to deadline-window schedules. | A scraper returning nothing is indistinguishable from a quiet week, and this data backs public claims about named officials. But Feb-Apr genuinely produces almost nothing because of the in-session ban (D74), so demanding rows year-round would cry wolf every spring and train everyone to ignore it. |
| D85 | 2026-09-20 | **Download manifests are committed to git permanently**; raw CSVs are 90-day artifacts only. | CSVs are far too large for git and GitHub artifacts expire, which would leave no durable evidence trail for CI-collected data. Manifests total ~416 KB and carry a SHA-256 per file, so what was downloaded and when remains provable after artifacts are gone. |
| D86 | 2026-09-20 | **The filing deadline dates in `docs/filing_calendar.md` are UNVERIFIED.** | No published calendar found on tn.gov/tref, and asserting unchecked statutory dates would be worse than flagging them. Confirm with the Registry (registry.info@tn.gov) — reasonable to ask alongside the bulk data request. Consequence of error is small: the weekly baseline catches any filing within 7 days, so a wrong date costs timeliness, never completeness. **In an election year, add the pre-primary and pre-general dates to the cron** — the standing quarterly windows will not cover them. |
| D87 | 2026-09-20 | The TREF sync re-runs `match_tref propose/link` and `classify donors` after every load. | New filers and new donors appear constantly; without re-matching, a newly elected member's money stays unlinked and uncategorised until a human happens to notice. |
| D88 | 2026-09-20 | **Comparisons are scoped to the current General Assembly, never all-time.** | All-time totals rank members by length of service. Garrett reads as **2.31x the chamber median** on lifetime figures but **0.96x — slightly BELOW it** — when compared only on the 114th GA. Publishing the 2.31x beside his name would have been materially misleading, about the project's own primary test subject. `f_legislator_finance_period()` (migration 0011) is now used for every ratio and baseline; the all-time figure stays on a member's own profile as their history. |
| D89 | 2026-09-20 | **Phase 8 does NOT use Evidence.dev.** The site is a custom Python static generator. | Evidence pivoted to a hosted product ("Evidence Studio") — the npm template is deprecated and prints deprecation notices for every script. The open-source package (MIT, v40.1.8) still exists but was last published Feb 2026. Options were: an unmaintained ~500 MB npm dependency, a third-party host holding our database credentials and deploying somewhere other than Cloudflare, or ~600 lines of Python matching the rest of the stack. Chose the last. |
| D90 | 2026-09-20 | **The language rules are enforced at build time and the build FAILS on a violation** (`language.py`). | PLAN.md Phase 8 forbids "violated", "illegal", "corrupt" and similar. Rules that rely on discipline get broken by a tired edit or a contributor who never read the plan. Verbatim source text (bill titles, donor names) is exempt via `class="verbatim"` — a bill titled "AN ACT relating to criminal offenses" is evidence, not our prose. Attribution to LegiScan is checked on every page (D45). |
| D91 | 2026-09-20 | The site queries Postgres **at build time only**; the browser never contacts Supabase. | No credential reaches a visitor, and the deny-all RLS posture from D55 stays intact with no anon key in client code. This is a better security position than PLAN.md anticipated, and it removes the Phase 8 concern flagged in `docs/security_audit.md`. |
| D92 | 2026-09-20 | The deploy workflow **refuses to publish a build of fewer than 50 pages**. | A near-empty build almost always means the database was unreachable. Without the guard, a transient outage would replace a working public site with nothing. |
| D93 | 2026-09-20 | **The review queue is one row per (legislator, industry), not per bill.** | The per-bill form double-counts: bills introduced days apart share overlapping windows, so the same contributions are counted against each. Gary Hicks appeared four times at exactly $22,020 from the same 16 donors — one pattern wearing four faces, which a reader would add up to $88,080. This is the same underlying error as D71 (fan-out) and D73 (overlapping windows), appearing for the third time. Grouping cut 388 rows to ~107 real patterns. |
| D94 | 2026-09-20 | Ranked by **subject-matched dollars alone**, never a composite score. | A weighted score hides the judgement inside a number and is the first thing a legislator's office would attack. Every other factor is a visible column instead. |
| D95 | 2026-09-20 | **VERIFICATION FOUND A REAL ERROR — $184,500 miscategorised.** The healthcare rule `HOSPITAL` also matched **HOSPITALITY**. | Tennessee Hospitality PAC, Ryman Hospitality, and 12 restaurant and hotel donors were counted as health care money. Found only by reading a generated report line by line against its sources, exactly as PLAN.md Phase 9 instructs. `NURSE` likewise matched `NURSERY`. Fixed to `HOSPITAL(?!ITY)` and `NURSE\b`; Jack Johnson's health care figure fell from $33,750 to $28,750. **`tests/test_classify.py` now guards this class of collision** — every case in it was a real production error. |
| D96 | 2026-09-20 | Thresholds live in `review_thresholds` and the methodology page **reads them from the database**. | The published page therefore always states the values actually in force, rather than a number someone forgot to update. |
| D97 | 2026-09-20 | Bill-level verification against capitol.tn.gov passed. | SB1283: sponsor `*Johnson`, "Filed for introduction 02/06/2025", Public Chapter 46, subject Public Health — matching our sponsor, introduced date, status and industry exactly. Confirms `introduced_date` derived as the earliest history entry is correct. |
| D98 | 2026-09-20 | The data dictionary is **generated from the live database**, never hand-written. | A hand-maintained dictionary drifts from the schema and then misleads the people using it to check our work. Column notes come from the migrations' COMMENT statements, so the reason a column exists sits beside its definition and is published automatically. |
| D99 | 2026-09-20 | PLAN.md's monthly checks are **automated** (`healthcheck.py` + a workflow that opens an issue on the 1st). | A checklist someone has to remember gets skipped, and the failure mode is silent — stale data that still looks fine. First run correctly flagged the missing 2023 contributions (FAIL), 95 unconfirmed filer names, and $11.6M of uncategorised organisation donors. |
| D100 | 2026-09-20 | `CONTRIBUTING.md` leads with **how to prove the project wrong**, and invites corrections from legislators and their staff explicitly. | The project's only real defence is that anyone can check it. It names the weakest links — donor classification, name matching, timing — and cites the $184,500 hospitality error as evidence that more remain. Handling corrections publicly and fast is itself evidence of good faith. |
| D101 | 2026-09-20 | **2023's repeated failures were a retry bug, not a TREF data problem.** `raise_for_status()` was called OUTSIDE `_retrying`, so an HTTP 500 was raised after the retry wrapper had already returned. | The 500 never reached the retry logic, so one transient server hiccup discarded hours of successful downloading. `_retrying` now also retries 5xx and 429 with longer backoff, and every status check happens inside the wrapper. 4xx still fails fast — that means our request is wrong and repeating it would repeat the mistake. Verified: the 2023 search that had failed twice now succeeds in 8 seconds. |
| D102 | 2026-09-20 | Added contributor-type partitioning (`fetch_year(..., only_from=)`) as a fallback for oversized years. | TREF holds the paging cursor in server-side session state. The four contributor types partition the result set exactly, so a year too large to page through in one session can be fetched as four shorter ones. **Not currently needed** — 2023 works once retries are fixed — but kept for when a year grows beyond a single session's endurance. |
| D103 | 2026-09-20 | The `.pagebanner` count is **per batch, not a year total**. | 2022 reports 559 on its first page against 165,154 actual rows. Do not use it to validate coverage or compare partitions; it misled an attempt to check the partition logic. |
| D104 | 2026-09-21 | **`_retrying` now catches `requests.RequestException`, the base class** — not a list of subclasses. | Listing subclasses failed three times in a row. First `HTTPError` escaped because `raise_for_status()` sat outside the wrapper. Then **`ChunkedEncodingError` escaped — it inherits from `RequestException`, not `ConnectionError` — and discarded 532 successfully downloaded batches** because batch 533 ended prematurely. Enumerating transient failures is a losing game over thousands of requests; catch the base and carve out only 4xx, which means our request is wrong. |
| D105 | 2026-09-21 | Years can be fetched **partitioned by contributor type, with a checkpoint per partition** (`--partitioned`). | TREF's paging cursor is server-side session state and cannot be resumed, so any failure discarded the entire year — brutal for 2023 at ~2 hours per attempt. The four contributor types partition the result set exactly, giving four shorter sessions and four checkpoints. A completed partition is marked done and skipped on rerun, so a failure now costs one partition rather than the year. |
| D106 | 2026-09-21 | **Latent bug found: `backfill` had no `--force` argument**, but the Phase 7 TREF sync workflow passes it. | The scheduled TREF job would have crashed with "unrecognized arguments" on its first run. Found incidentally while adding `--partitioned`. Both flags now exist. **Nothing had ever exercised that workflow end to end** — the secrets are not set yet, so it has never run. |
| D107 | 2026-09-21 | **Scope widened to every disclosed influence channel** — recorded as governing principle 4. | User direction. Researched the live sources first: TCA § 3-6-305 gift ban and its three event exceptions; In-State Events 2006-2026 (sponsor-level, **attendees never named by statutory design**); SS-8011 employer reports (**ranges, no per-member detail**, but authoritative employer→subject matter); SS-8004 Statements of Interest (**the only per-member channel**: income sources, directorships, investments, sponsored travel Q8B, lobbying ties, retainers, leadership PACs; structured HTML; 220 Reps + 49 Senators listable). Full findings in `docs/influence_channels.md`. **No design decision made yet** — awaiting approval. |
| D108 | 2026-09-21 | SS-8004 Q15 (leadership PACs) explains `GARRETT PAC`: it is Johnny Garrett's own declared leadership PAC (GARRETTPAC); Sexton's is CAMPAC. | Resolves a Phase 4 ambiguity from the authoritative source rather than by name similarity. A member's leadership PAC can be linked to them deliberately and labelled, not guessed. |
| D109 | 2026-09-21 | iLobby dashboards list archived reports as `<option value="viewExpenditureReport.htm?reportId=N">End Year 2025</option>` — the value is a URL, not an id, and the label spans lines. | The first fetcher regex matched nothing and would have collected only "current" reports. Fixed and verified against a saved dashboard (finds End/Mid Year 2025). The 2025 run already in flight uses the old code; a rerun fills the archived reports since existing files are skipped. |
| D110 | 2026-09-21 | **Filer→legislator matching treats chamber as a preference (−8), never a filter.** | LegiScan's 114th GA data lists Sen. London Lamar as House; the Ethics Commission lists her as Senator. A hard chamber filter found her no candidate at all. Mismatches are flagged in `match_method` and held for review rather than auto-approved. Also: a 2-letter given-name prefix (ED→EDWARD) counts when the surname is exact. |
| D111 | 2026-09-21 | **Declared leadership PACs key-join to TREF filers 18 for 18** once punctuation and spaces are stripped. Part D is a plain join. | JACK PAC ↔ "JACK - PAC" ($1.37M), MCPAC ($3.45M), BOW-PAC ↔ both "BOW-PAC" and "BOWPAC". `v_leadership_pac_finance` shows these **beside** a member's figures, labelled, and they are **never added to the member's own totals** — a leadership PAC is a separate committee the member controls. |
| D112 | 2026-09-21 | The language linter's verbatim exemption now spans nested elements (backreference to the opening tag). | It stopped at the first closing tag of any element, so a verbatim `<ul>` lost its exemption at the first `</li>` and a filer's declared client interest "CIVIL & CRIMINAL LITIGATION" failed the build. That is source text, not our prose. `tests/test_language.py` pins the edge. |
| D113 | 2026-09-21 | **Source-data corrections are logged in `data_corrections`** (old value, new value, source URL, who verified, when), never made by silent edit; raw columns are never touched. First entry: London Lamar → Senate, District 33, per capitol.tn.gov 2026-09-21. | The site had been publishing her as a Representative on LegiScan's word. A correction to data about a named person has to be as checkable as the data itself. |
| D114 | 2026-09-21 | **Sponsored events (Phase 11B) are stored and shown at sponsor level only, never joined to a member.** 1,631 events 2006-2026, $12.97M reported. | The legal condition for these events (TCA § 3-6-305(b)(8)) is that the entire General Assembly is invited, so attendance is never recorded. Attributing an event to a member would be fabrication. The page says this above the data. |
| D115 | 2026-09-21 | The first iLobby fetcher run matched every archived report URL as "current" and pulled ~30 reports per employer. | The `viewExpenditureReport.htm?reportId=` pattern also appears inside each archived `<option value>`. Killed and relaunched on a regex anchored to `Current: <a href=…>`, with the year filter for archived ones; files already fetched are kept and skipped. Manifest now written every 25 employers so the loader can run mid-fetch. |
| D116 | 2026-09-21 | **An employer's industry is the first subject it listed in its latest report** that maps to a specific industry — never an alphabetical aggregate. | `array_agg(DISTINCT …)` sorts alphabetically, which made BNSF Railway "manufacturing" (economic & industrial development sorts before transportation) and Belz Investco "legal" (corrections before property interests). The filer's own ordering is the signal. |
| D117 | 2026-09-21 | Donors whose name keys to a registered employer of lobbyists take that employer's declared industry at confidence 95, `assigned_by='ss8011'`; human-reviewed rows are never overwritten. | This is the authoritative replacement for name-pattern classification that Phase 6 intended (D80, D95). Coverage grows as the 1,156-employer fetch completes. |
| D118 | 2026-09-21 | Filer→legislator matching compares the filer's chamber to the legislator's seat **in that report year's General Assembly**, not the current one; exact full names score 100; recognised diminutives (MICHAEL/MIKE) score 95. | London Lamar's 2021-22 filings say Representative, which she was. G.A. Hardaway scored 84 against his own exact name because single-letter tokens were dropped. Review queue fell accordingly; genuinely uncertain cases remain held. |
| D119 | 2026-09-21 | **iLobby subject matters describe what an employer lobbies about, not what it is.** Only industry-type subjects classify an employer; issue subjects (taxation, labor, crime & criminal procedure, economic development…) map to `other`; the employer's name is the fallback and `industry_source` records which applied. | Declared-order selection (D116) was necessary but not sufficient: BNSF Railway still came out "manufacturing" from "economic & industrial development", Belz Investco "legal" from "crime & criminal procedure". A donor is overridden only by a *declared* industry — a name guess must never override a name guess. |
| D120 | 2026-09-21 | **Employer industry: name pattern first, declared industry-type subject only as a gap-filler, `other` otherwise; the SS-8011 donor pass is insert-only and never overrides.** Supersedes the precedence in D119. | Even industry-type subjects are what an employer lobbies *about*: AEP/Kingsport Power declares "insurance" because it lobbies on insurance. The name "POWER" is the better signal. A declared subject may add coverage for an uninformative name; it must not outrank an informative one. (Also: the first attempt at this patch failed on a syntax error and ran the old logic; the rows it wrote were removed before re-running.) |
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

## Domain and email

- **Domain: wethepoliticianstn.com**, transferred to Cloudflare 2026-09-20; nameservers
  propagating. This is the Phase 8 production host.
- **Project email: wethepoliticianstn@gmail.com** — use this for all outbound project
  correspondence (TREF, TAP, LegiScan, Ethics Commission) rather than a personal address,
  so the record stays in one inbox.

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

## Action required before the scheduled jobs can run

Add two **repository secrets** at
https://github.com/We-the-Politicians-TN/tn-accountability/settings/secrets/actions

| Secret | Value |
|---|---|
| `DATABASE_URL` | The Supabase **session pooler** string (port 5432). The direct host is IPv6-only and GitHub runners cannot reach it — D18. |
| `LEGISCAN_API_KEY` | The LegiScan key already in your Keychain. |
| `CLOUDFLARE_API_TOKEN` | Cloudflare -> My Profile -> API Tokens -> Edit Cloudflare Workers |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare dashboard sidebar |

Then trigger each workflow once by hand (Actions -> select workflow -> Run workflow)
to confirm it works before relying on the schedule.

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
