-- =============================================================================
-- 0005_legiscan_fields.sql
--
-- Fields the LegiScan dataset provides that the schema had no home for, plus one
-- honesty marker.
--
-- `change_hash` is the important one: Phase 7's daily update compares LegiScan's
-- per-bill hash against the stored value and re-fetches only bills that actually
-- changed. Without it, staying current means re-pulling everything.
--
-- `legislator_terms.source` exists because LegiScan person records do not carry
-- official term start and end dates. What we can derive is "this person appears in
-- this General Assembly", whose year range is NOT the same thing as a certified
-- term. Recording how a row was derived keeps a convenient approximation from
-- being mistaken later for an authoritative date.
-- =============================================================================

BEGIN;

ALTER TABLE bills
    ADD COLUMN change_hash text,          -- LegiScan per-bill change detection
    ADD COLUMN bill_type_raw text,
    ADD COLUMN session_id   integer,      -- LegiScan session identifier
    ADD COLUMN completed    boolean;

CREATE INDEX bills_change_hash_idx ON bills (change_hash);
CREATE INDEX bills_session_id_idx ON bills (session_id);

COMMENT ON COLUMN bills.change_hash IS
    'LegiScan change hash. Phase 7 compares this to detect which bills actually '
    'changed, instead of re-fetching every bill.';

ALTER TABLE legislators
    ADD COLUMN person_hash text,
    ADD COLUMN role_raw    text;          -- 'Rep' / 'Sen' as published

ALTER TABLE roll_calls
    ADD COLUMN total smallint,
    ADD COLUMN legiscan_bill_id integer;

ALTER TABLE legislator_terms
    ADD COLUMN source text;

COMMENT ON COLUMN legislator_terms.source IS
    'How this row was derived. ''legiscan_session'' means the dates are the General '
    'Assembly''s year range, NOT certified term dates — the person merely appears in '
    'that session. Do not present these as official term boundaries.';

COMMIT;
