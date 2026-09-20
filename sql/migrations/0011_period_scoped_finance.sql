-- =============================================================================
-- 0011_period_scoped_finance.sql — make the baseline comparable
--
-- `v_legislator_finance` totals a member's ENTIRE history. Comparing those totals
-- across members is not a like-for-like comparison: someone who has served since
-- 2019 will show roughly four times the money of someone elected in 2024, purely
-- from length of service. Published beside a name as "2.3x the chamber median",
-- that would be misleading.
--
-- This adds a period-scoped version. Members are compared only on money raised
-- within the same window, against peers who were serving in that window.
--
-- The all-time view is kept: it is the right figure for a member's own profile
-- ("raised since 2019"), just not for comparing one member to another.
-- =============================================================================

BEGIN;

CREATE FUNCTION f_legislator_finance_period(
    p_from date,
    p_to   date DEFAULT NULL
)
RETURNS TABLE (
    legislator_id bigint, legislator text, party text, chamber chamber, district text,
    contribution_count bigint, total_raised numeric,
    pac_total numeric, individual_total numeric, pac_share_pct numeric,
    top10_total numeric, top10_concentration_pct numeric, total_spent numeric
) AS $$
    SELECT l.id, l.full_name_raw, l.party, l.chamber, l.district,
           f.cnt, f.total, f.pac, f.indiv,
           CASE WHEN f.total > 0 THEN round(100.0 * f.pac / f.total, 1) END,
           t.top10,
           CASE WHEN f.total > 0 THEN round(100.0 * t.top10 / f.total, 1) END,
           e.spent
    FROM legislators l
    LEFT JOIN LATERAL (
        SELECT count(*) AS cnt, coalesce(sum(amount),0) AS total,
               coalesce(sum(amount) FILTER (WHERE donor_class(donor_name)='pac'),0) AS pac,
               coalesce(sum(amount) FILTER (WHERE donor_class(donor_name)='individual'),0) AS indiv
        FROM contributions
        WHERE recipient_legislator_id = l.id
          AND contribution_date >= p_from
          AND (p_to IS NULL OR contribution_date <= p_to)
    ) f ON true
    LEFT JOIN LATERAL (
        SELECT coalesce(sum(s),0) AS top10 FROM (
            SELECT sum(amount) AS s FROM contributions
            WHERE recipient_legislator_id = l.id AND donor_name IS NOT NULL
              AND contribution_date >= p_from
              AND (p_to IS NULL OR contribution_date <= p_to)
            GROUP BY donor_name ORDER BY 1 DESC NULLS LAST LIMIT 10) q
    ) t ON true
    LEFT JOIN LATERAL (
        SELECT coalesce(sum(amount),0) AS spent FROM expenditures
        WHERE spender_legislator_id = l.id
          AND expenditure_date >= p_from
          AND (p_to IS NULL OR expenditure_date <= p_to)
    ) e ON true
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION f_legislator_finance_period IS
    'Finance totals within a date window, so members can be compared like for like. '
    'Use this for any baseline or ratio. The all-time v_legislator_finance is correct '
    'for a member''s own profile but NOT for comparing members of differing tenure.';

COMMIT;
