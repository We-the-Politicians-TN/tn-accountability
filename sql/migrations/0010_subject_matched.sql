-- =============================================================================
-- 0010_subject_matched.sql — the subject-matched signal
--
-- For each sponsorship, how much came from donors in the SAME industry as the
-- bill's own subject, inside the lookback window.
--
-- Phase 5 established that raw pre-introduction totals measure the legislative
-- calendar rather than the bill (D73): Tennessee's in-session contribution ban
-- pushes all fundraising into the interim, so every bill's lookback window lands
-- on the same fundraising peak and every member looks identical. Restricting to
-- donors whose industry matches the bill's subject is what distinguishes one bill
-- from another, and one legislator from their peers.
--
-- Three exclusions are built in rather than left to the caller:
--   * ceremonial bills (memorial resolutions have no industry — D from 0009)
--   * unapproved TREF name matches (already excluded upstream: only approved
--     matches set recipient_legislator_id)
--   * uncategorised donors (counted separately so coverage is always visible)
--
-- Money and bill aggregates are computed in separate scopes throughout (D71).
-- =============================================================================

BEGIN;

CREATE FUNCTION f_subject_matched(
    lookback_days int DEFAULT 90,
    p_general_assembly int DEFAULT NULL,
    p_legislator_id bigint DEFAULT NULL
)
RETURNS TABLE (
    legislator_id     bigint,
    legislator        text,
    party             text,
    chamber          chamber,
    bill_id           bigint,
    bill_number       text,
    bill_title        text,
    introduced_date   date,
    sponsor_type      sponsor_type,
    bill_categories   text[],
    matched_total     numeric,
    matched_count     bigint,
    matched_donors    text[],
    all_pre_intro_total numeric
) AS $$
    WITH bill_cat AS (
        -- A bill's industries, via its LegiScan subjects. Ceremonial bills are
        -- excluded outright: a memorial honouring a retiring teacher has no
        -- industry, and pairing one with donor money would be indefensible.
        SELECT b.id AS bill_id,
               array_agg(DISTINCT scm.category) FILTER (WHERE scm.category IS NOT NULL) AS cats
        FROM bills b
        LEFT JOIN LATERAL unnest(b.subjects) AS s(subject) ON true
        LEFT JOIN subject_category_map scm ON scm.subject = s.subject
        WHERE NOT coalesce(b.is_ceremonial, false)
          AND (p_general_assembly IS NULL OR b.general_assembly = p_general_assembly)
        GROUP BY b.id
    )
    SELECT
        l.id, l.full_name_raw, l.party, l.chamber,
        b.id, b.bill_number, b.title, b.introduced_date, s.sponsor_type,
        bc.cats,
        coalesce(mm.total, 0), coalesce(mm.cnt, 0), mm.donors,
        coalesce(ap.total, 0)
    FROM sponsorships s
    JOIN bills b       ON b.id = s.bill_id
    JOIN bill_cat bc   ON bc.bill_id = b.id
    JOIN legislators l ON l.id = s.legislator_id
    -- Money from donors whose industry matches one of the bill's own industries.
    LEFT JOIN LATERAL (
        SELECT sum(c.amount) AS total, count(*) AS cnt,
               array_agg(DISTINCT c.donor_name) AS donors
        FROM contributions c
        JOIN donor_category_map dcm ON dcm.donor_name = c.donor_name
        WHERE c.recipient_legislator_id = l.id
          AND bc.cats IS NOT NULL
          AND dcm.category = ANY (bc.cats)
          AND c.contribution_date >= b.introduced_date - (lookback_days || ' days')::interval
          AND c.contribution_date <  b.introduced_date
    ) mm ON true
    -- The unrestricted total, kept alongside so the two can be compared and the
    -- calendar effect stays visible rather than hidden.
    LEFT JOIN LATERAL (
        SELECT sum(c.amount) AS total FROM contributions c
        WHERE c.recipient_legislator_id = l.id
          AND c.contribution_date >= b.introduced_date - (lookback_days || ' days')::interval
          AND c.contribution_date <  b.introduced_date
    ) ap ON true
    WHERE b.introduced_date IS NOT NULL
      AND (p_legislator_id IS NULL OR l.id = p_legislator_id)
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION f_subject_matched IS
    'PRIMARY SIGNAL: contributions from donors in the same industry as a sponsored '
    'bill''s subject, within the lookback window. Excludes ceremonial bills. Works '
    'for every legislator (governing principle 1), never for one subject.';

COMMIT;
