-- =============================================================================
-- 0002_tref_source_columns.sql
--
-- The initial schema was written from PLAN.md's description of the data. Having
-- now pulled real files from TREF, several published columns had nowhere to go:
--
--   contributions: Type, Adj, Election Year
--   expenditures:  Type, Adj, Election Year, Candidate For, S/O
--
-- Dropping them would break the project's core rule — every table keeps the raw
-- source text alongside any cleaned version — so this adds a home for each.
--
-- TREF's "Type" is the transaction type (Monetary / In-Kind / Independent), not
-- the donor type; `contributions.donor_type` already means something different
-- and is left alone.
-- =============================================================================

BEGIN;

-- --- contributions -----------------------------------------------------------

ALTER TABLE contributions
    ADD COLUMN transaction_type_raw text,   -- 'Monetary', 'In-Kind', 'Independent'
    ADD COLUMN transaction_type     text,
    ADD COLUMN adjustment_raw       text,   -- 'Y' / 'N'
    ADD COLUMN is_adjustment        boolean,
    ADD COLUMN election_year_raw    text,
    ADD COLUMN election_year        smallint;

COMMENT ON COLUMN contributions.transaction_type IS
    'TREF "Type": monetary, in-kind, or independent expenditure. Distinct from donor_type.';
COMMENT ON COLUMN contributions.is_adjustment IS
    'TREF "Adj" flag. Adjustments amend a previously reported figure; including them '
    'alongside the original double-counts, so analysis views must decide explicitly.';

CREATE INDEX contributions_election_year_idx ON contributions (election_year);
CREATE INDEX contributions_txn_type_idx ON contributions (transaction_type);

-- --- expenditures ------------------------------------------------------------

ALTER TABLE expenditures
    ADD COLUMN transaction_type_raw text,
    ADD COLUMN transaction_type     text,
    ADD COLUMN adjustment_raw       text,
    ADD COLUMN is_adjustment        boolean,
    ADD COLUMN election_year_raw    text,
    ADD COLUMN election_year        smallint,
    ADD COLUMN candidate_for_raw    text,   -- office the spending relates to
    ADD COLUMN candidate_for        text,
    ADD COLUMN support_oppose_raw   text,   -- TREF "S/O": supporting or opposing
    ADD COLUMN support_oppose       text;

COMMENT ON COLUMN expenditures.support_oppose IS
    'TREF "S/O": whether an independent expenditure supported or opposed the named '
    'candidate. Reversing this reverses the meaning of the record.';

CREATE INDEX expenditures_election_year_idx ON expenditures (election_year);

-- --- provenance --------------------------------------------------------------
-- The backfill loads one (search_type, year) at a time and must be able to tell
-- whether that slice is already in the database.

ALTER TABLE data_pulls
    ADD COLUMN search_type text,
    ADD COLUMN data_year   smallint;

CREATE INDEX data_pulls_slice_idx ON data_pulls (source, search_type, data_year);

COMMIT;
