# STATUS — project state and decision record

**Purpose.** This file is the durable memory of the project. Claude Code's context
window gets truncated between and within sessions; this file is what survives.
It records *decisions and why they were made*, not just tasks completed, so that
any future session can reconstruct the reasoning without replaying the history.

**Every session:** read `PLAN.md` and this file before doing anything. At the end,
append to the Session log and add any new entries to Decisions.

---

## Current phase

**Phase 0 — Accounts and workspace.** Scaffold complete locally; GitHub push pending.

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
3. Phase 1 — write and apply the Postgres schema migration. Blocked on `DATABASE_URL`.

---

## Blockers

- **`gh` CLI not installed**, so the repo cannot be created from this machine
  programmatically. Either install it (`brew install gh`, which first needs
  Homebrew) or create the repo in the GitHub web UI and run:
  ```
  git remote add origin https://github.com/<user>/tn-accountability.git
  git push -u origin main
  ```
- **No Supabase `DATABASE_URL`.** Phase 1's migration can be *written* without it
  but not *applied*.
- **No `LEGISCAN_API_KEY`.** Required for Phase 3.

---

## Session log

Newest first. One entry per session.

### 2026-09-13 — Phase 0 scaffold

- Created directory structure, `git init` on `main`.
- Wrote `.gitignore` (secrets + large data excluded), `.env.example`, `README.md`,
  `PLAN.md` (full build plan), `STATUS.md`, `requirements.txt`.
- Created `.venv` on Python 3.9.6 and installed dependencies.
- **Verified:** `git check-ignore .env` confirms `.env` is ignored; `git status`
  shows no data or secret files staged.
- **Not verified:** nothing pushed to GitHub yet (`gh` missing).
- **Next:** push to GitHub, then Phase 1 schema.
