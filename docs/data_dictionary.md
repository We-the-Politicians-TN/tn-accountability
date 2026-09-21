# Data dictionary

Generated from the live database on 2026-09-20. Do not edit by hand — run
`python -m tn_accountability.data_dictionary` instead.

This exists so anyone can check our work: what we store, where it came from, and
which columns are the original source text as published versus our cleaned version.

## The rules that shape this schema

**Raw text is always kept.** Columns ending `_raw` hold exactly what the source
published. The matching column without the suffix holds our cleaned version. Where
they disagree, the `_raw` column is the evidence. Where a value could not be parsed —
a filing dated 29 February in a non-leap year, for example — the raw text is kept and
the cleaned column is left empty. We do not guess.

**Nothing enters without provenance.** Every financial record carries a
`data_pull_id` pointing at the ingest run that loaded it, plus the source file and
line it came from, so any figure can be traced to a downloaded file.

**Unapproved matches are never counted.** A campaign finance filer name is attributed
to a legislator only after a human confirms the match. Until then it counts for
no one — we would rather understate than misattribute.

---

## `bills`
*38,613 rows.*

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | bigint | no |  |
| `legiscan_bill_id` | integer | no |  |
| `session_name` | text | yes |  |
| `general_assembly` | smallint | yes |  |
| `session_year_start` | smallint | yes |  |
| `bill_number` | text | no |  |
| `bill_type` | text | yes |  |
| `title` | text | yes |  |
| `description` | text | yes |  |
| `subjects` | text[] | no |  |
| `subject_category` | text | yes |  |
| `committee` | text | yes |  |
| `introduced_date` | date | yes |  |
| `last_action` | text | yes |  |
| `last_action_date` | date | yes |  |
| `status` | text | yes |  |
| `status_raw` | text | yes | Source text exactly as published. |
| `passed` | boolean | no |  |
| `passed_date` | date | yes |  |
| `legiscan_url` | text | yes |  |
| `state_url` | text | yes |  |
| `data_pull_id` | bigint | yes |  |
| `created_at` | timestamp with time zone | no |  |
| `updated_at` | timestamp with time zone | no |  |
| `change_hash` | text | yes | LegiScan change hash. Phase 7 compares this to detect which bills actually changed, instead of re-fetching every bill. |
| `bill_type_raw` | text | yes | Source text exactly as published. |
| `session_id` | integer | yes |  |
| `completed` | boolean | yes |  |
| `is_ceremonial` | boolean | yes | Memorial/recognition resolution with no policy content. EXCLUDE from every analysis and from published sponsorship counts: pairing a memorial with donor money is meaningless, and 92-95% of resolutions are ceremonial. |

## `contributions`
*1,326,743 rows.*

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | bigint | no |  |
| `contribution_date` | date | yes |  |
| `contribution_date_raw` | text | yes | Source text exactly as published. |
| `amount` | numeric(14,2) | yes |  |
| `amount_raw` | text | yes | Source text exactly as published. |
| `donor_name_raw` | text | yes | Source text exactly as published. |
| `donor_name` | text | yes |  |
| `donor_type` | donor_type | no |  |
| `donor_id` | bigint | yes |  |
| `donor_employer_raw` | text | yes | Source text exactly as published. |
| `donor_employer` | text | yes |  |
| `donor_occupation_raw` | text | yes | Source text exactly as published. |
| `donor_occupation` | text | yes |  |
| `donor_address_raw` | text | yes | Source text exactly as published. |
| `donor_city` | text | yes |  |
| `donor_state` | text | yes |  |
| `donor_zip` | text | yes |  |
| `recipient_name_raw` | text | yes | Source text exactly as published. |
| `recipient_name` | text | yes |  |
| `recipient_legislator_id` | bigint | yes |  |
| `recipient_committee` | text | yes |  |
| `source_report` | text | yes |  |
| `source_report_date` | date | yes |  |
| `source_record_id` | text | yes |  |
| `source_file` | text | yes |  |
| `data_pull_id` | bigint | no |  |
| `created_at` | timestamp with time zone | no |  |
| `transaction_type_raw` | text | yes | Source text exactly as published. |
| `transaction_type` | text | yes | TREF "Type": monetary, in-kind, or independent expenditure. Distinct from donor_type. |
| `adjustment_raw` | text | yes | Source text exactly as published. |
| `is_adjustment` | boolean | yes | TREF "Adj" flag. Adjustments amend a previously reported figure; including them alongside the original double-counts, so analysis views must decide explicitly. |
| `election_year_raw` | text | yes | Source text exactly as published. |
| `election_year` | smallint | yes |  |
| `description_raw` | text | yes | TREF "Description" — for in-kind contributions, often the only record of what was given. |
| `description` | text | yes |  |

## `data_pulls`
*16 rows.*

One row per ingest run. Every imported record points back here so any number can be traced to its source file and run.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | bigint | no |  |
| `source` | ingest_source | no |  |
| `started_at` | timestamp with time zone | no |  |
| `finished_at` | timestamp with time zone | yes |  |
| `status` | text | no |  |
| `rows_added` | integer | no |  |
| `rows_updated` | integer | no |  |
| `rows_skipped` | integer | no |  |
| `source_files` | text[] | no |  |
| `notes` | text | yes |  |
| `error` | text | yes |  |
| `search_type` | text | yes |  |
| `data_year` | smallint | yes |  |

## `donor_category_map`
*1,035 rows.*

Donor -> industry assignments. `reviewed` records human confirmation. Unreviewed assignments are usable for exploration but must be labelled provisional wherever they reach a reader.

| Column | Type | Null | Notes |
|---|---|---|---|
| `donor_name` | text | no |  |
| `category` | text | no |  |
| `confidence` | numeric(5,2) | yes |  |
| `assigned_by` | text | no |  |
| `reviewed` | boolean | no |  |
| `notes` | text | yes |  |

## `donors`
*0 rows.*

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | bigint | no |  |
| `canonical_name` | text | no |  |
| `donor_type` | donor_type | no |  |
| `industry_category` | text | yes |  |
| `industry_source` | text | yes |  |
| `category_reviewed` | boolean | no |  |
| `employer` | text | yes |  |
| `city` | text | yes |  |
| `state` | text | yes |  |
| `lobbyist_employer_id` | bigint | yes |  |
| `notes` | text | yes |  |
| `data_pull_id` | bigint | yes |  |
| `created_at` | timestamp with time zone | no |  |
| `updated_at` | timestamp with time zone | no |  |

## `expenditures`
*233,586 rows.*

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | bigint | no |  |
| `expenditure_date` | date | yes |  |
| `expenditure_date_raw` | text | yes | Source text exactly as published. |
| `amount` | numeric(14,2) | yes |  |
| `amount_raw` | text | yes | Source text exactly as published. |
| `vendor_name_raw` | text | yes | As published by TREF. Nullable: some filings report an amount and purpose with no payee named. Do not substitute a placeholder. |
| `vendor_name` | text | yes |  |
| `purpose_raw` | text | yes | Source text exactly as published. |
| `purpose` | text | yes |  |
| `vendor_address_raw` | text | yes | Source text exactly as published. |
| `vendor_city` | text | yes |  |
| `vendor_state` | text | yes |  |
| `vendor_zip` | text | yes |  |
| `spender_name_raw` | text | yes | Source text exactly as published. |
| `spender_name` | text | yes |  |
| `spender_legislator_id` | bigint | yes |  |
| `spender_committee` | text | yes |  |
| `source_report` | text | yes |  |
| `source_report_date` | date | yes |  |
| `source_record_id` | text | yes |  |
| `source_file` | text | yes |  |
| `data_pull_id` | bigint | no |  |
| `created_at` | timestamp with time zone | no |  |
| `transaction_type_raw` | text | yes | Source text exactly as published. |
| `transaction_type` | text | yes |  |
| `adjustment_raw` | text | yes | Source text exactly as published. |
| `is_adjustment` | boolean | yes |  |
| `election_year_raw` | text | yes | Source text exactly as published. |
| `election_year` | smallint | yes |  |
| `candidate_for_raw` | text | yes | Source text exactly as published. |
| `candidate_for` | text | yes |  |
| `support_oppose_raw` | text | yes | Source text exactly as published. |
| `support_oppose` | text | yes | TREF "S/O": whether an independent expenditure supported or opposed the named candidate. Reversing this reverses the meaning of the record. |

## `industry_categories`
*18 rows.*

| Column | Type | Null | Notes |
|---|---|---|---|
| `code` | text | no |  |
| `label` | text | no |  |
| `description` | text | yes |  |

## `legislator_terms`
*564 rows.*

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | bigint | no |  |
| `legislator_id` | bigint | no |  |
| `chamber` | chamber | no |  |
| `district` | text | no |  |
| `party` | text | yes |  |
| `general_assembly` | smallint | yes |  |
| `start_date` | date | no |  |
| `end_date` | date | yes |  |
| `data_pull_id` | bigint | yes |  |
| `source` | text | yes | How this row was derived. 'legiscan_session' means the dates are the General Assembly's year range, NOT certified term dates — the person merely appears in that session. Do not present these as official term boundaries. |

## `legislator_tref_ids`
*269 rows.*

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | bigint | no |  |
| `legislator_id` | bigint | no |  |
| `tref_candidate_id` | text | yes |  |
| `tref_name_raw` | text | no | Source text exactly as published. |
| `tref_name` | text | no |  |
| `match_confidence` | numeric(5,2) | yes |  |
| `match_method` | text | yes |  |
| `approved` | boolean | no | Unapproved matches must never feed a published number. Phase 4 requires human sign-off below 90% confidence. |
| `approved_by` | text | yes |  |
| `approved_at` | timestamp with time zone | yes |  |
| `notes` | text | yes |  |
| `data_pull_id` | bigint | yes |  |
| `created_at` | timestamp with time zone | no |  |

## `legislators`
*207 rows.*

Every person who served in a covered session, not just current members.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | bigint | no |  |
| `legiscan_people_id` | integer | yes |  |
| `full_name_raw` | text | no | Source text exactly as published. |
| `full_name` | text | no |  |
| `first_name` | text | yes |  |
| `middle_name` | text | yes |  |
| `last_name` | text | yes |  |
| `suffix` | text | yes |  |
| `nickname` | text | yes |  |
| `party` | text | yes |  |
| `chamber` | chamber | yes |  |
| `district` | text | yes |  |
| `ballotpedia_url` | text | yes |  |
| `opensecrets_id` | text | yes |  |
| `votesmart_id` | integer | yes |  |
| `data_pull_id` | bigint | yes |  |
| `created_at` | timestamp with time zone | no |  |
| `updated_at` | timestamp with time zone | no |  |
| `person_hash` | text | yes |  |
| `role_raw` | text | yes | Source text exactly as published. |

## `lobbyist_employers`
*0 rows.*

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | bigint | no |  |
| `employer_name_raw` | text | no | Source text exactly as published. |
| `employer_name` | text | no |  |
| `registration_years` | smallint[] | no |  |
| `issue_areas` | text[] | no |  |
| `industry_category` | text | yes |  |
| `address_raw` | text | yes | Source text exactly as published. |
| `city` | text | yes |  |
| `state` | text | yes |  |
| `source_file` | text | yes |  |
| `data_pull_id` | bigint | yes |  |
| `created_at` | timestamp with time zone | no |  |

## `lobbyists`
*0 rows.*

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | bigint | no |  |
| `lobbyist_name_raw` | text | no | Source text exactly as published. |
| `lobbyist_name` | text | no |  |
| `lobbyist_employer_id` | bigint | yes |  |
| `registration_years` | smallint[] | no |  |
| `source_file` | text | yes |  |
| `data_pull_id` | bigint | yes |  |

## `review_thresholds`
*4 rows.*

Values in force for the review queue. Identical for every legislator; party is never an input. Changing a value here changes what the public site shows, so the methodology page reads from this table rather than restating numbers.

| Column | Type | Null | Notes |
|---|---|---|---|
| `name` | text | no |  |
| `value` | numeric | no |  |
| `unit` | text | yes |  |
| `description` | text | no |  |
| `updated_at` | timestamp with time zone | no |  |

## `roll_calls`
*48,490 rows.*

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | bigint | no |  |
| `legiscan_roll_call_id` | integer | no |  |
| `bill_id` | bigint | no |  |
| `vote_date` | date | yes |  |
| `description` | text | yes |  |
| `chamber` | chamber | yes |  |
| `yea` | smallint | yes |  |
| `nay` | smallint | yes |  |
| `not_voting` | smallint | yes |  |
| `absent` | smallint | yes |  |
| `passed` | boolean | yes |  |
| `data_pull_id` | bigint | yes |  |
| `total` | smallint | yes |  |
| `legiscan_bill_id` | integer | yes |  |

## `sponsorships`
*134,030 rows.*

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | bigint | no |  |
| `bill_id` | bigint | no |  |
| `legislator_id` | bigint | no |  |
| `sponsor_type` | sponsor_type | no |  |
| `sponsor_order` | smallint | yes |  |
| `sponsored_date` | date | yes |  |
| `data_pull_id` | bigint | yes |  |

## `subject_category_map`
*194 rows.*

| Column | Type | Null | Notes |
|---|---|---|---|
| `subject` | text | no |  |
| `category` | text | no |  |
| `assigned_by` | text | no |  |
| `reviewed` | boolean | no |  |
| `notes` | text | yes |  |

## `votes`
*2,472,724 rows.*

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | bigint | no |  |
| `roll_call_id` | bigint | no |  |
| `bill_id` | bigint | no |  |
| `legislator_id` | bigint | no |  |
| `vote` | vote_cast | no |  |
| `vote_raw` | text | yes | Source text exactly as published. |
| `data_pull_id` | bigint | yes |  |

---

## Analysis functions and views

### `f_legislator_finance_period()`

Finance totals within a date window, so members can be compared like for like. Use this for any baseline or ratio. The all-time v_legislator_finance is correct for a member's own profile but NOT for comparing members of differing tenure.

### `f_review_queue()`

Phase 9 review queue. Identical thresholds for every member; party is never an input and there is no manual addition or removal. Ranked by subject-matched dollars alone, deliberately not by a composite score.

### `f_review_queue_grouped()`

Review queue at one row per (legislator, industry). Each contribution is counted exactly once even when several bills share an overlapping window — the per-bill form double-counts. Thresholds from review_thresholds, identical for everyone.

### `f_sponsor_windows()`

Cross-reference analysis for ANY legislator (D65: the method must work for everyone, not one subject). lookback_days is configurable, default 90.

### `f_subject_matched()`

PRIMARY SIGNAL: contributions from donors in the same industry as a sponsored bill's subject, within the lookback window. Excludes ceremonial bills. Works for every legislator (governing principle 1), never for one subject.

### `v_legislator_finance` (view)

One row per legislator. Every aggregate is computed in its own LATERAL so that money is never multiplied by bill counts (D71).

---

## Thresholds currently in force

| Setting | Value | What it does |
|---|---|---|
| `lookback_days` | 90 days | Window before a bill's introduction in which contributions are counted. |
| `min_matched_donors` | 2 donors | Minimum distinct donors in the matching industry. A single donor is a coincidence, not a pattern. |
| `min_matched_total` | 2500 dollars | Minimum contributions from the bill's own industry within the window for a pair to appear. |
| `min_ratio_to_median` | 1.0 ratio | Member's current-Assembly fundraising relative to their chamber median. 1.0 = at the median. |
