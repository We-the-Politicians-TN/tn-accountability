# Schema — how the tables connect

Plain-English companion to `sql/migrations/0001_initial_schema.sql`.

## The shape of it

There are three families of tables, plus a provenance log that ties everything together.

**Money** — `contributions`, `expenditures`, `donors`
**Legislating** — `bills`, `sponsorships`, `roll_calls`, `votes`
**People and identity** — `legislators`, `legislator_terms`, `legislator_tref_ids`
**Context** — `lobbyist_employers`, `lobbyists`
**Provenance** — `data_pulls`

The whole point of the project is the join between the first two families, and
that join runs through `legislators`. Everything else exists to make that join
trustworthy.

```
                        ┌──────────────┐
                        │  data_pulls  │  every row below points back here
                        └──────┬───────┘
                               │
      ┌────────────────────────┼─────────────────────────┐
      │                        │                         │
┌─────▼──────┐         ┌───────▼────────┐        ┌───────▼────────┐
│contributions│        │  legislators   │        │     bills      │
│expenditures │───────▶│                │◀───────│                │
└─────┬───────┘ recipient/  ├──────────┐ │ sponsorships  ├─────────┐
      │         spender     │          │ │ votes         │         │
      │                ┌────▼─────┐ ┌──▼─▼──────────┐    │    ┌────▼──────┐
      │                │  terms   │ │ tref_ids      │    │    │roll_calls │
      │                └──────────┘ └───────────────┘    │    └───────────┘
      │                                                   │
┌─────▼──────┐                                    ┌───────▼────────┐
│   donors   │───── industry_category ───────────▶│ subject_category│
└─────┬──────┘          (the match)               └────────────────┘
      │
┌─────▼──────────────┐
│ lobbyist_employers │──── lobbyists
└────────────────────┘
```

## Table by table

**`data_pulls`** — one row per ingest run: which source, when it started and
finished, how many rows it added, which raw files it read, and whether it failed.
Every imported record carries a `data_pull_id`. This is what makes a number on the
public site traceable back to a file on disk.

**`legislators`** — one row per person who served in a covered session, current or
not. Keyed to LegiScan's `people_id` where available. Holds the name in both raw
and normalized form plus a `nickname` column, because nicknames are what make the
Phase 4 matching hard ("Johnny" vs "John W.").

**`legislator_terms`** — a legislator serves several terms, possibly in different
chambers or districts, so terms are their own rows with start and end dates and a
General Assembly number.

**`legislator_tref_ids`** — a legislator's campaign-finance identities. TREF files
under names like "Committee to Elect Jane Doe", and one person can have several.
Phase 4 fills this in by name matching and writes a `match_confidence`; the
`approved` flag stays false until a human signs off. **Analysis views must filter
on `approved = true`** — an unapproved guess must never reach a published figure.

**`contributions`** — money in. The donor appears as raw text plus a normalized
name plus, once Phase 6 clusters them, a `donor_id`. The recipient is likewise raw
text plus a nullable `recipient_legislator_id`, nullable because a committee may
not yet be matched to a person. Indexed on `(recipient_legislator_id,
contribution_date)` because the central query is "what did this legislator receive
between these two dates".

**`expenditures`** — money out, same shape: vendor raw and normalized, purpose,
spender as raw text plus nullable legislator link.

**`donors`** — the normalized entity behind many raw donor name variants. Carries
`donor_type` (individual / PAC / business / party) and `industry_category`, which
is the column the subject-matched signal depends on. `category_reviewed` records
whether a human has confirmed the category.

**`bills`** — LegiScan bill records: number, title, session, introduced date,
status, passed flag and date. `subjects` holds LegiScan's own labels as published;
`subject_category` holds our assigned category, which is what gets matched against
a donor's industry.

**`sponsorships`** — which legislator sponsored which bill, and whether as primary
or co-sponsor.

**`roll_calls` and `votes`** — a roll call is one recorded vote event on a bill,
with its totals; `votes` records how each legislator voted in it.

**`lobbyist_employers` and `lobbyists`** — Tennessee Ethics Commission
registrations. These supply the issue areas that seed donor industry categories,
which is what turns a raw timing coincidence into a subject-matched signal.

## Two rules the schema enforces

**Raw text is always kept.** Columns ending in `_raw` hold exactly what the source
published; the unsuffixed column holds the cleaned version. When they disagree,
the raw column is the evidence. This is why `contribution_date_raw` is `text` —
a source date that doesn't parse is preserved rather than dropped.

**Nothing enters without provenance.** `contributions.data_pull_id` and
`expenditures.data_pull_id` are `NOT NULL`. You cannot load a financial record
without recording where it came from.

## Deduplication

`contributions` and `expenditures` each carry a partial unique index on
`(source_file, source_record_id)`. Re-running an ingest over the same file will
not double-count rows that carry a source identifier. Rows without one fall back
to application-level checks — a known soft spot, flagged for Phase 7.

## Not yet in the schema

- Analysis views (Phase 5) — the lookback-window and subject-match logic.
- The patterns-for-review queue and its thresholds (Phase 9).

Both land as later migrations.
