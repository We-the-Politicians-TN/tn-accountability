# Influence channels in Tennessee — what is disclosed, and where

Researched 2026-09-21 against the live sources. This records what exists so a design
can be built on facts rather than assumptions. Nothing here is a design decision.

## The legal frame, which shapes everything

**TCA § 3-6-305 bans lobbyists and employers of lobbyists from giving gifts to
legislators**, and bans legislators from accepting them. The "free lunch for one
legislator" is, in Tennessee, mostly prohibited rather than merely undisclosed.
What the statute *permits* is narrow and is what generates data:

| Exception | What it allows | Limits (2025, inflation-adjusted every 2 yrs) | Disclosed where |
|---|---|---|---|
| (b)(8) In-state events | Entertainment/refreshments where the **entire General Assembly** is invited | $78 per person per day; invitation filed 7 days before; cost report within 30 days | In-State Events pages |
| (b)(9) Speaking events | Events where the official speaks or sits on a panel, paid by membership orgs | Same $78/person/day | In-State Events pages |
| (b)(10) Employer meals | Meals from an employer of lobbyists, officer/management present | $78 per event, **$158 per person per year**; only members not drawing per diem | SS-8011 aggregates |

Consequence: a company cannot lawfully buy one legislator lunch to discuss a bill. It
can host the whole General Assembly at $78 a head and must publish that it did.

## Channel 1 — In-State Events (Ethics Commission, 2006–2026)

- One HTML table per year at
  `tn.gov/tec/tec-lobbyist/tec-in-state-events/<year>-in-state-events.html`.
- Columns: event date, event name, **sponsor**, total expense, expense per person,
  invitation (PDF/image), disclosure (PDF).
- 2025: 91 events, 171 documents. Per-person costs run $3 (cookies and coffee) to
  $76 (Grizzlies training camp); totals up to $58,773 (BNA concourse reception).
- The disclosure form (read: `disclosureid.1735.pdf`) names the **sponsoring employer
  or lobbyist, the submitter, date, description, total and per-person cost**.
- **Attendees are never named.** This is structural, not an omission: the legal
  condition is that everyone was invited, so nobody records who came.

So this channel is *sponsor → General Assembly*, never *sponsor → member*. It can
show which industries spend money hosting the legislature, and how much, and can be
joined to the same sponsor's contributions and lobbying — but it cannot be attributed
to an individual legislator, and doing so would be fabrication.

## Channel 2 — Lobbying Expenditure Reports, SS-8011 (iLobby)

- Public search at `ilobbysearch.app.tn.gov/ilobbysearch/search.htm`. Form POST;
  requires `request=employerSearch` plus `employerName`, `employerSubjectMatter`,
  `employerYear` (2008–2026). Blank name lists all: **1,156 employers in 2025**.
- Each employer has `viewEmployerDashboard.htm?employerId=N` listing its registered
  lobbyists by year and its semiannual reports, `viewExpenditureReport.htm?reportId=N`.
- A report contains: contact and leadership names, **nature of business as subject
  matters** (e.g. "health & health care; insurance"), total lobbyist compensation
  **as a range** ($350,000–$400,000), lobbying-related expenses as a range (<$10,000),
  aggregate of in-state events.
- **No per-legislator detail, and no exact dollars.** Ranges only.

Its real value is different: it is the authoritative **employer → subject matter**
mapping that Phase 6 always intended to use in place of name-pattern guessing (see
D80, D95). Amazon, HCA, the Bankers Association are all in here with their declared
subjects.

## Channel 3 — Statement of Disclosure of Interests, SS-8004 (per legislator)

The only per-member channel. Filed annually by April 15 under penalty of perjury
(TCA § 8-50-507); civil penalties to $10,000 for failure (§ 3-6-205). Public search at
`conflict.app.tn.gov/conflict/search.htm`; each filing is **structured HTML** at
`view_form_8004.htm?name=&id=&f=&v=1`.

- Listing by position works: **Representative → 220 filers (2026, includes
  candidates), Senator → 49**, paginated 25 per page.
- Sections and what the law requires in each:

| Q | Section | Must disclose |
|---|---|---|
| 4A | Sources of income | Every private source > $200 for filer and spouse — employers, directorships, business income, honoraria, lecture fees, rental income. Names only, no amounts. |
| 5 | Positions held | Officer, director, trustee, partner, proprietor of any business or nonprofit, with dates. |
| 7 | Investments | Any holding > $10,000 or > 5% of a business. Names only. |
| **8A** | **Legislative expenses** | **Amount and source of any private contribution defraying legislative duties** (not state-reimbursed). |
| **8B** | **Travel** | **Amount and source of travel paid by "a person with an interest in Tennessee state public policy"** to inform or advise the member. |
| 9 | Lobbying | Any entity for which the filer's spouse, associate or minor child lobbies; any lobbying firm the filer holds an interest in. |
| 10 | Professional services | For licensed professions (law, medicine, accounting…), the **general interests of clients** served by filer or spouse. |
| 11 | Retainer fees | Any retainer from a person or firm that lobbies the General Assembly. |
| 13 | Loans | Any loan > $1,000 in the prior year, with exclusions for banks and family. |
| **15** | **Leadership PACs** | Any multi-candidate committee the member established or controlled in the last 5 years. |

**Q8 is the sponsored-travel-and-benefits channel to a named member.** Both filings
read so far (Garrett, Sexton) report "None" there. Whether that is typical is the
first thing a full ingest will answer.

Examples of what it does contain:
- Garrett: income from Spencer Fane LLP and Garrett Enterprise; spouse at Nashville
  Fertility Center; profession "Law — attorney, general business"; leadership PAC
  **GARRETTPAC**.
- Sexton: income from Aflac Insurance and One Bank; **director of One Bank** since
  2015; spouse at TruPharm; leadership PAC **CAMPAC**.

**Q15 resolves an open ambiguity from Phase 4.** `GARRETT PAC` in the campaign finance
data (D69's sibling entry) is Johnny Garrett's own leadership PAC, declared here. A
member's leadership PAC money can now be linked to them deliberately and labelled as
such, instead of being held apart as an unmatched filer.

## What no dataset captures

Stating this plainly is part of the method, not a weakness of it:

- Meals or gifts that were never disclosed. The law bans most of them; the data shows
  only what was reported.
- Who attended a sponsored event.
- Dollar amounts of income, investments or lobbying compensation — Tennessee
  requires names and ranges, not figures.
- Anything about *why* a member voted. Every channel here records what was received
  or held, never motive. The site does not infer motive (governing principle 3).
