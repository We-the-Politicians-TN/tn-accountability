-- =============================================================================
-- 0017_sponsored_events.sql — Phase 11B
--
-- In-state events lobbyists and their employers host for the General Assembly,
-- permitted by TCA § 3-6-305(b)(8)-(9) only when the ENTIRE membership is invited,
-- capped per person per day, and reported within 30 days. Published by the Ethics
-- Commission as one table per year, 2006 onward.
--
-- What this can and cannot say: it records who hosted the legislature and what it
-- cost. It never records who attended, because the legal condition is that everyone
-- was invited. So an event is sponsor -> General Assembly, and is NEVER attributed
-- to an individual member. Any join to a legislator would be fabrication.
-- =============================================================================

BEGIN;

CREATE TABLE sponsored_events (
    id                 bigserial PRIMARY KEY,
    event_year         smallint NOT NULL,
    event_date_raw     text NOT NULL,          -- '2025-11-18-12-5', '2025-08-02/03' occur
    event_date         date,                   -- first date where parseable
    event_name_raw     text NOT NULL,
    sponsor_raw        text NOT NULL,           -- may name several sponsors or venues
    sponsor            text,                    -- normalised for matching
    total_expense_raw  text,
    total_expense      numeric(14,2),
    per_person_raw     text,
    per_person         numeric(10,2),
    invitation_url     text,
    disclosure_url     text,
    source_file        text NOT NULL,
    row_index          smallint NOT NULL,
    data_pull_id       bigint NOT NULL REFERENCES data_pulls(id),
    UNIQUE (source_file, row_index)
);
CREATE INDEX sponsored_events_year_idx    ON sponsored_events (event_year);
CREATE INDEX sponsored_events_sponsor_idx ON sponsored_events (sponsor);
ALTER TABLE sponsored_events ENABLE ROW LEVEL SECURITY;
COMMENT ON TABLE sponsored_events IS
    'Events hosted for the whole General Assembly. Sponsor-level only: attendees are '
    'never recorded, so never attribute one to a member.';

COMMIT;
