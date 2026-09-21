-- =============================================================================
-- 0013_review_queue_grouped.sql — one pattern per row
--
-- The per-bill queue in 0012 double-counts. Bills introduced within days of each
-- other have overlapping lookback windows, so the SAME contributions are counted
-- against each one. Gary Hicks appeared four times at exactly $22,020 from the same
-- 16 healthcare donors — one pattern wearing four faces. A reader scanning that
-- queue would infer $88,080.
--
-- This is the third appearance of one underlying mistake: counting the same money
-- more than once (D71 fan-out, D73 overlapping windows). Here the grain is fixed so
-- it cannot recur: one row per (legislator, industry), each contribution counted
-- exactly once, with the bills it relates to listed alongside.
--
-- The resulting statement is also simply truer: "received $22,020 from 16 health
-- care donors in the 90 days before introducing 4 health care bills" is one claim
-- that can be checked, rather than four that cannot be added up.
-- =============================================================================

BEGIN;

CREATE FUNCTION f_review_queue_grouped(
    p_general_assembly int  DEFAULT 114,
    p_period_from      date DEFAULT '2025-01-01'
)
RETURNS TABLE (
    legislator_id     bigint,
    legislator        text,
    party             text,
    chamber          chamber,
    district          text,
    industry          text,
    bill_numbers      text[],
    bill_count        bigint,
    first_introduced  date,
    last_introduced   date,
    matched_total     numeric,
    matched_donors    bigint,
    member_raised     numeric,
    chamber_median    numeric,
    ratio_to_median   numeric
) AS $$
    WITH th AS (
        SELECT (SELECT value FROM review_thresholds WHERE name='lookback_days')::int AS lookback,
               (SELECT value FROM review_thresholds WHERE name='min_matched_total')   AS min_matched,
               (SELECT value FROM review_thresholds WHERE name='min_ratio_to_median') AS min_ratio,
               (SELECT value FROM review_thresholds WHERE name='min_matched_donors')::int AS min_donors
    ),
    fin AS (
        SELECT f.* FROM f_legislator_finance_period(p_period_from) f
        WHERE EXISTS (SELECT 1 FROM legislator_terms t
                      WHERE t.legislator_id=f.legislator_id AND t.general_assembly=p_general_assembly)
    ),
    med AS (
        SELECT chamber, (percentile_cont(0.5) WITHIN GROUP (ORDER BY total_raised))::numeric AS m
        FROM fin WHERE total_raised > 0 GROUP BY chamber
    ),
    -- Every (legislator, industry, bill) where the bill concerns that industry.
    pairs AS (
        SELECT s.legislator_id, b.id AS bill_id, b.bill_number, b.introduced_date,
               scm.category AS industry
        FROM sponsorships s
        JOIN bills b ON b.id = s.bill_id
        JOIN LATERAL unnest(b.subjects) AS sub(subject) ON true
        JOIN subject_category_map scm ON scm.subject = sub.subject
        WHERE s.sponsor_type = 'primary'
          AND b.general_assembly = p_general_assembly
          AND NOT coalesce(b.is_ceremonial, false)
          AND b.introduced_date IS NOT NULL
        GROUP BY 1,2,3,4,5
    ),
    -- Each contribution counted ONCE per (legislator, industry): it qualifies if it
    -- falls inside the window of ANY bill of that industry, not once per bill.
    matched AS (
        SELECT p.legislator_id, p.industry,
               c.id AS contribution_id, c.amount, c.donor_name
        FROM pairs p
        CROSS JOIN th
        JOIN contributions c
          ON c.recipient_legislator_id = p.legislator_id
         AND c.contribution_date >= p.introduced_date - (th.lookback || ' days')::interval
         AND c.contribution_date <  p.introduced_date
        JOIN donor_category_map dcm
          ON dcm.donor_name = c.donor_name AND dcm.category = p.industry
        GROUP BY 1,2,3,4,5
    ),
    agg AS (
        SELECT legislator_id, industry,
               sum(amount) AS matched_total,
               count(DISTINCT donor_name) AS matched_donors
        FROM matched GROUP BY 1,2
    ),
    bills_agg AS (
        SELECT legislator_id, industry,
               array_agg(DISTINCT bill_number ORDER BY bill_number) AS bill_numbers,
               count(DISTINCT bill_id) AS bill_count,
               min(introduced_date) AS first_introduced,
               max(introduced_date) AS last_introduced
        FROM pairs GROUP BY 1,2
    )
    SELECT a.legislator_id, l.full_name_raw, l.party, l.chamber, l.district,
           a.industry, ba.bill_numbers, ba.bill_count,
           ba.first_introduced, ba.last_introduced,
           a.matched_total, a.matched_donors,
           fin.total_raised, med.m,
           CASE WHEN med.m > 0 THEN round(fin.total_raised / med.m, 2) END
    FROM agg a
    JOIN bills_agg ba ON ba.legislator_id=a.legislator_id AND ba.industry=a.industry
    JOIN legislators l ON l.id = a.legislator_id
    JOIN fin ON fin.legislator_id = a.legislator_id
    JOIN med ON med.chamber = l.chamber
    CROSS JOIN th
    WHERE a.matched_total  >= th.min_matched
      AND a.matched_donors >= th.min_donors
      AND med.m > 0
      AND fin.total_raised / med.m >= th.min_ratio
    ORDER BY a.matched_total DESC
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION f_review_queue_grouped IS
    'Review queue at one row per (legislator, industry). Each contribution is counted '
    'exactly once even when several bills share an overlapping window — the per-bill '
    'form double-counts. Thresholds from review_thresholds, identical for everyone.';

COMMIT;
