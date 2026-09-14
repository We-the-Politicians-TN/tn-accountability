# Tennessee Legislator Accountability Platform — Build Plan

**How to use this document.** Each phase has three parts: what you set up yourself (accounts, clicks), what you tell Claude Code (copy the prompt, adjust as needed), and how you verify the result without reading code. Do the phases in order; don't start a phase until the previous one's checks pass. Expect Phase 0–3 to take a few focused sessions; the rest is iterative.

**Ground rules for every Claude Code session**
- Start each session by telling it: *"Read PLAN.md and STATUS.md before doing anything."* (You'll create these in Phase 0.) This keeps it oriented across sessions.
- End each session by telling it: *"Update STATUS.md with what was done, what's verified, and what's next."*
- Ask it to explain anything you don't understand. If an explanation still doesn't make sense, that's a sign the approach is too complicated — say so.
- Never let it delete or overwrite raw downloaded data. Raw files are your evidence trail.

---

## Phase 0 — Accounts and workspace (you do this, ~1 hour)

Create these accounts (all free to start):

| Account | Purpose | Note |
|---|---|---|
| GitHub | Code, scheduled jobs, public transparency | Make the repository **public** from day one |
| Supabase | Hosted Postgres database | Free tier; note the connection string and keys |
| LegiScan | Bill/sponsor/vote data | Request a free API key at legiscan.com |
| Accountability Project (publicaccountability.org) | Historical contributions/expenditures | Requires a MuckRock login to download |
| Cloudflare | Hosts the public site (Workers with static assets), DNS, DDoS protection | Free tier; no bandwidth charges |

Install on your machine: Git (git-scm.com) and Node.js (nodejs.org, LTS version). Claude Code can walk you through both if you ask.

Create a folder called `tn-accountability` and open it in Claude Code. First prompt:

> Create a new project for a Tennessee legislator accountability platform. Set up a Python project with a virtual environment, a `.gitignore` that excludes secrets and large data files, a `.env.example` file listing the secrets I'll need (Supabase connection string, LegiScan API key), and a README. Create `PLAN.md` containing the following plan [paste this whole document] and an empty `STATUS.md`. Initialize git and push to a new public GitHub repo called tn-accountability. Explain each file you created in one sentence.

**Verify:** You can see the repo on GitHub with those files. Secrets are NOT visible in the repo (open `.gitignore` and confirm `.env` is listed).

---

## Phase 1 — Database schema (one session)

> Design and create a Postgres schema in my Supabase database for tracking Tennessee state legislators. Tables needed: `legislators` (name, chamber, district, party, terms served with start/end dates, LegiScan people_id, TREF candidate IDs — a legislator can have several), `contributions` (date, amount, donor raw name, donor normalized name, donor type: individual/PAC/business, donor employer, occupation, address, source report, recipient legislator or committee), `expenditures` (date, amount, vendor raw name, vendor normalized, purpose, recipient), `donors` (normalized entity with type and industry tag), `bills` (LegiScan bill_id, session, number, title, subjects, introduced date, last action, status, passed flag, passed date), `sponsorships` (bill, legislator, sponsor type: primary/co-sponsor, date), `votes` (bill, roll call, legislator, vote cast), `lobbyist_employers` (employer name, lobbyists, registration years, issue areas), and `data_pulls` (log of every ingest run: source, timestamp, rows added). Every table must keep the raw source text alongside any cleaned version. Write the SQL as a migration file, run it, and produce a plain-English diagram or description of how the tables connect.

**Verify:** In Supabase → Table Editor you see all the tables. Ask Claude Code: *"Show me the description of the schema again"* and confirm it matches what you asked for.

---

## Phase 2 — Historical backfill (one to two sessions)

Download the Tennessee contributions and expenditures files from the Accountability Project into a `data/raw/accountability_project/` folder. Do not rename them.

> Import the Accountability Project Tennessee contributions and expenditures CSVs in `data/raw/accountability_project/` into the `contributions` and `expenditures` tables. Preserve their original columns as raw fields and use their normalized columns for the cleaned fields. Do not modify the raw files. Log the import in `data_pulls`. When finished, report: total rows imported per table, date range covered, the 20 largest donors by total amount, and the 10 legislators who received the most. Then look up the Accountability Project's GitHub repo (irworkshop/accountability_datacleaning) and summarize in `docs/data_cleaning_notes.md` what cleaning they applied to the Tennessee data.

**Verify (do these yourself):**
- Row counts should be roughly 2.0M contributions and 480K expenditures.
- Pick three contributions from the "largest donors" list, search for them on apps.tn.gov/tncamp, and confirm they exist with matching amount and date.
- Search the Garrett records: ask *"Show me every contribution to Johnny Garrett in 2024 with date, donor, and amount."* Compare against your existing workbook. They should match.

---

## Phase 3 — Bills, sponsors, and votes from LegiScan (one session)

> Using my LegiScan API key, download the full dataset for every Tennessee session from the 111th General Assembly (2019) through the current one. Use LegiScan's bulk dataset endpoints rather than one call per bill to stay within the free quota. Load bills, sponsorships (primary vs. co-sponsor), and roll-call votes into the schema. Populate `legislators` from LegiScan's people data, including everyone who served in those sessions, not just current members. Log the pull. Report: bills per session, number of legislators loaded per chamber, and any bills with a missing introduction date.

**Verify:**
- Ask: *"List every bill Johnny Garrett was primary sponsor on in the 114th GA with introduction dates."* Compare against your workbook's Bills tab (50 bills). Counts and dates should match.
- Spot-check two bills on capitol.tn.gov — introduction date should match.
- Ask: *"How many current House members and Senate members are in the legislators table?"* Should be 99 and 33.

---

## Phase 4 — Link legislators to their campaign records (one session, possibly messy)

This is the step most projects get wrong. A legislator's TREF records are filed under candidate names that may not match LegiScan names (nicknames, middle initials, "Committee to Elect...").

> Match each legislator in `legislators` to their TREF candidate names in the contributions and expenditures data. Use name matching plus district and office to propose matches. Produce a CSV of proposed matches with a confidence score and show me the ones below 90% confidence so I can approve or correct them. Do not apply low-confidence matches without my approval.

**Verify:** Review the low-confidence list yourself. For 10 random legislators, ask for their total contributions and check the number looks plausible against their TREF filings.

---

## Phase 5 — Reproduce the Garrett analysis in SQL (one session)

This is the calibration step. If the database can reproduce your spreadsheet, the pipeline is sound.

> Write SQL views that reproduce my existing cross-reference analysis for any legislator: for each bill they sponsored, total contributions received in the N days before introduction (N configurable, default 90), contributions from the same donors in the N days after passage, and a flag when the pre-introduction total exceeds a threshold. Run it for Johnny Garrett and compare to the Cross-Reference tab of `Garrett_Donations_Bills_Tracker.xlsx` (I'll upload it). Explain any differences.

Then, the baseline:

> Run the same analysis for every legislator in the 114th GA. Compute the chamber median and each member's ratio to the median for: total raised, share from PACs vs. individuals, top-10 donor concentration, and pre-introduction contribution totals. Show me the distribution. I expect nearly everyone's fundraising to cluster in pre-session months because of the in-session contribution ban — confirm whether that's what the data shows.

**Verify:** The Garrett numbers match your workbook (or differences are explained and make sense). The pre-session clustering is visible for essentially all members, confirming timing alone can't be the signal.

---

## Phase 6 — Donor industry tagging and subject matching (two or more sessions)

> Download Tennessee lobbyist and lobbyist-employer registrations from the Tennessee Ethics Commission website into `data/raw/tec/` and load them into `lobbyist_employers`. Then build a `donors` table by clustering contribution donor names into single entities (e.g., variants of the same PAC or company). Assign each donor entity an industry category. Start with: any donor that is a registered lobbyist employer gets that employer's issue areas; PACs get categorized by name; leave individuals uncategorized unless employer is known. Give me a review file of the 200 largest donor entities with their proposed category so I can correct them.

> Assign each bill a subject category using LegiScan subjects and committee assignments. Then create a view that, for each sponsorship, shows contributions from donors in the *same* industry category as the bill's subject within the lookback window. This "subject-matched" number is the primary signal; the raw timing number is secondary.

**Verify:** Review the top-200 donor categories yourself — this is where your domain knowledge matters most. Spot-check five subject-matched flags by reading the bill and the donor's business.

---

## Phase 7 — Forward ingest automation (one to two sessions)

> Build a scraper using Playwright that pulls new contributions and expenditures from apps.tn.gov/tncamp for all state legislative candidates since the last pull date, saves the raw downloads to `data/raw/tref/YYYY-MM-DD/`, and loads new rows without duplicating existing ones. Build a second job that polls LegiScan for new or updated bills, sponsorships, and votes. Schedule both as GitHub Actions: TREF weekly (daily in the two weeks around each filing deadline), LegiScan daily during session. Send me an email or GitHub notification if a run fails or adds zero rows when rows were expected.

**Verify:** Trigger a run manually from the GitHub Actions tab; it completes and `data_pulls` shows a new row. A week later, check that it ran on its own.

> Add the Tennessee campaign finance filing calendar to `docs/` and make sure the scraper schedule reflects it. Note that the TREF site could change its layout; document in STATUS.md how to tell if the scraper broke.

---

## Phase 8 — Public site (two sessions)

> Build an Evidence site (evidence.dev) connected to the Supabase database with: (1) a home page explaining the project, methodology, and data sources; (2) a legislator index with sortable columns for the baseline-relative metrics; (3) a profile page per legislator showing contributions over time, top donors, expenditures by vendor, sponsored bills with the timing and subject-matched analysis, and their metrics vs. chamber median; (4) a methodology page with the exact formulas; (5) a "patterns for review" page. Deploy to Cloudflare as a Worker with static assets (not a Cloudflare Pages project — Pages is being phased out in favor of Workers). Connect it to the GitHub repo so every push rebuilds the site, and store the Supabase credentials as Cloudflare environment variables, never in the repo.

> Because Evidence pre-builds every page at deploy time, the site will show stale numbers after an ingest run until it rebuilds. Add a final step to both GitHub Actions ingest jobs (Phase 7) that triggers a Cloudflare rebuild whenever new rows were loaded. Confirm it works by running an ingest manually and checking that the live site updates within a few minutes.

**Verify:** The site is reachable at its `workers.dev` address (or your custom domain once you add it in Cloudflare DNS). Push a small text change to the repo and confirm the live site updates.

**Language rules for the site — tell Claude Code these explicitly:**
- Never use "violated," "illegal," or "corrupt." Use "flagged for review," "pattern," "exceeds chamber median."
- Every flag states the specific pattern, the numbers, and the statutory provision or ethics-code section it may relate to (Titles 2, 3, 8; House and Senate ethics codes).
- Every flag links to the TREF complaint page and the Ethics Commission so any reader can file.
- The methodology page includes the in-session-contribution-ban caveat and explains why timing alone is not used as a signal.

**Verify:** Open the live site on your phone. Read the Garrett page as if you were his staff — is every claim on it backed by a number you could defend?

---

## Phase 9 — Review queue and reporting helper (one session)

> Add a "patterns for review" view listing legislator-bill pairs where subject-matched contributions exceed a threshold AND the legislator's ratio to chamber median is above a cutoff. Rank by strength of pattern. For each, generate a draft summary in neutral language with all supporting records listed by source and date, formatted so it could be attached to a TREF or Ethics Commission complaint. Make thresholds configurable and document the current values on the methodology page.

**Verify:** Take one flagged pattern and check every supporting record against the original TREF filing and bill page. If anything doesn't hold up, fix the logic before publishing.

---

## Phase 10 — Publish and harden (ongoing)

- Ask Claude Code to write a `CONTRIBUTING.md` and a data dictionary so others can check your work.
- Before public launch, have two people who aren't you review five legislator pages for errors.
- Add a "report a data error" link on every page.
- Keep the repo and cleaned data public — open methodology is your defense against claims of bias.
- Once stable, extend backward to earlier General Assemblies (the backfill data goes to 2002).

---

## Checks to run every month

1. Did every scheduled run complete? (GitHub Actions tab)
2. Did the latest filing deadline's data appear? Pick one legislator, compare site vs. TREF.
3. Ask Claude Code: *"Are there new legislators, new sessions, or TREF site changes I need to handle?"*
4. Review new items in the patterns-for-review queue before they go live.
