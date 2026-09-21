-- =============================================================================
-- 0012_review_queue.sql — Phase 9 review queue
--
-- Legislator-bill pairs where money from the bill's own industry arrived close to
-- its introduction, and the member's fundraising is at or above their chamber's
-- median for the current Assembly.
--
-- RANKING: by subject-matched dollars alone. Not a weighted composite. A composite
-- is the first thing a legislator's office would attack, and rightly — it hides the
-- judgement inside a number. Every other factor is shown as its own column so a
-- reader weighs them for themselves.
--
-- NOT ranked by pre-introduction total. Phase 5 showed that measure tracks the
-- legislative calendar rather than the bill (D73): the in-session contribution ban
-- means nearly every member's bills sit on the same fundraising peak. Ranking by it
-- would surface whoever introduced bills nearest the fundraising season and present
-- that as a finding about a person.
--
-- Comparisons are scoped to the current General Assembly (D88), because lifetime
-- totals rank members by length of service.
-- =============================================================================

BEGIN;

-- Thresholds live in a table, not in code, so the methodology page can state the
-- values actually in force and changing them leaves a record.
CREATE TABLE review_thresholds (
    name        text PRIMARY KEY,
    value       numeric NOT NULL,
    unit        text,
    description text NOT NULL,
    updated_at  timestamptz NOT NULL DEFAULT now()
);

INSERT INTO review_thresholds (name, value, unit, description) VALUES
 ('lookback_days',        90,   'days',
  'Window before a bill''s introduction in which contributions are counted.'),
 ('min_matched_total',    2500, 'dollars',
  'Minimum contributions from the bill''s own industry within the window for a pair to appear.'),
 ('min_ratio_to_median',  1.0,  'ratio',
  'Member''s current-Assembly fundraising relative to their chamber median. 1.0 = at the median.'),
 ('min_matched_donors',   2,    'donors',
  'Minimum distinct donors in the matching industry. A single donor is a coincidence, not a pattern.');

COMMENT ON TABLE review_thresholds IS
    'Values in force for the review queue. Identical for every legislator; party is '
    'never an input. Changing a value here changes what the public site shows, so the '
    'methodology page reads from this table rather than restating numbers.';


CREATE FUNCTION f_review_queue(
    p_lookback_days   int     DEFAULT NULL,
    p_min_matched     numeric DEFAULT NULL,
    p_min_ratio       numeric DEFAULT NULL,
    p_min_donors      int     DEFAULT NULL,
    p_general_assembly int    DEFAULT 114,
    p_period_from     date    DEFAULT '2025-01-01'
)
RETURNS TABLE (
    legislator_id    bigint,
    legislator       text,
    party            text,
    chamber         chamber,
    district         text,
    bill_id          bigint,
    bill_number      text,
    bill_title       text,
    introduced_date  date,
    industries       text[],
    matched_total    numeric,
    matched_donors   bigint,
    window_total     numeric,
    matched_share_pct numeric,
    member_raised    numeric,
    chamber_median   numeric,
    ratio_to_median  numeric
) AS $$
    WITH th AS (
        SELECT
          coalesce(p_lookback_days, (SELECT value FROM review_thresholds WHERE name='lookback_days')::int) AS lookback,
          coalesce(p_min_matched,   (SELECT value FROM review_thresholds WHERE name='min_matched_total'))  AS min_matched,
          coalesce(p_min_ratio,     (SELECT value FROM review_thresholds WHERE name='min_ratio_to_median')) AS min_ratio,
          coalesce(p_min_donors,    (SELECT value FROM review_thresholds WHERE name='min_matched_donors')::int) AS min_donors
    ),
    fin AS (
        SELECT f.* FROM f_legislator_finance_period(p_period_from) f
        WHERE EXISTS (SELECT 1 FROM legislator_terms t
                      WHERE t.legislator_id=f.legislator_id AND t.general_assembly=p_general_assembly)
    ),
    med AS (
        -- percentile_cont returns double precision; cast so round(numeric,int) applies.
        SELECT chamber,
               (percentile_cont(0.5) WITHIN GROUP (ORDER BY total_raised))::numeric AS m
        FROM fin WHERE total_raised > 0 GROUP BY chamber
    ),
    sm AS (
        SELECT * FROM f_subject_matched((SELECT lookback FROM th), p_general_assembly)
        WHERE sponsor_type = 'primary'
    )
    SELECT
        sm.legislator_id, sm.legislator, sm.party, sm.chamber, l.district,
        sm.bill_id, sm.bill_number, sm.bill_title, sm.introduced_date,
        sm.bill_categories, sm.matched_total,
        coalesce(array_length(sm.matched_donors, 1), 0)::bigint,
        sm.all_pre_intro_total,
        CASE WHEN sm.all_pre_intro_total > 0
             THEN round(100.0 * sm.matched_total / sm.all_pre_intro_total, 1) END,
        fin.total_raised, med.m,
        CASE WHEN med.m > 0 THEN round(fin.total_raised / med.m, 2) END
    FROM sm
    JOIN legislators l ON l.id = sm.legislator_id
    JOIN fin ON fin.legislator_id = sm.legislator_id
    JOIN med ON med.chamber = sm.chamber
    CROSS JOIN th
    WHERE sm.matched_total >= th.min_matched
      AND coalesce(array_length(sm.matched_donors, 1), 0) >= th.min_donors
      AND med.m > 0
      AND fin.total_raised / med.m >= th.min_ratio
    ORDER BY sm.matched_total DESC
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION f_review_queue IS
    'Phase 9 review queue. Identical thresholds for every member; party is never an '
    'input and there is no manual addition or removal. Ranked by subject-matched '
    'dollars alone, deliberately not by a composite score.';

COMMIT;
