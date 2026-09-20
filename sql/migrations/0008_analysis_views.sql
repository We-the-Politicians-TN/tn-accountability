-- =============================================================================
-- 0008_analysis_views.sql — Phase 5 cross-reference analysis
--
-- Answers, for any legislator: for each bill they sponsored, how much did they
-- receive in the N days before it was introduced, and from donors who gave in that
-- window, how much came back in the N days after it passed.
--
-- THREE RULES ENCODED HERE, each learned the hard way:
--
-- 1. Money and bill counts are NEVER aggregated in the same join. Joining
--    contributions to sponsorships multiplies each contribution by the number of
--    bills, which once produced a $70.6M figure for a legislator who raised
--    $342,925 (D71). Every aggregate below is computed in its own scope.
--
-- 2. Only APPROVED name matches feed any figure. `recipient_legislator_id` is set
--    solely from approved rows in `legislator_tref_ids` (D8, D69).
--
-- 3. Timing alone is not a signal. Tennessee bans contributions while the General
--    Assembly is in session, so almost every member's fundraising clusters in the
--    same pre-session months. A pre-introduction total that looks striking in
--    isolation is usually just the calendar. This is why every measure is expressed
--    relative to the chamber, and why Phase 6's subject matching — not timing —
--    is the primary signal.
-- =============================================================================

BEGIN;

-- --- provisional donor classification ----------------------------------------
-- TREF does not publish a donor type, and every row currently reads 'unknown'.
-- This name-pattern classifier is a STOPGAP so the PAC-versus-individual measure
-- can be computed at all. Phase 6 replaces it with real entity resolution against
-- lobbyist-employer registrations. Anything built on this must say it is provisional.

CREATE FUNCTION donor_class(name text) RETURNS text AS $$
    SELECT CASE
        WHEN name IS NULL THEN 'unknown'
        WHEN name ~ '\m(PAC|PCC|POLITICAL ACTION|COMMITTEE|FUND FOR|CONFERENCE)\M' THEN 'pac'
        WHEN name ~ '\m(INC|LLC|L\.L\.C|CORP|CORPORATION|COMPANY|CO|LP|LLP|PLLC|
                        ASSOCIATION|ASSN|UNION|LOCAL|SOCIETY|LEAGUE|COUNCIL|GROUP|
                        PARTNERS|HOLDINGS|ENTERPRISES|SYSTEMS|SERVICES)\M' THEN 'business'
        WHEN name ~ '^[A-Z][A-Za-z .''-]+,\s*[A-Z]' THEN 'individual'
        ELSE 'unknown'
    END
$$ LANGUAGE sql IMMUTABLE;

COMMENT ON FUNCTION donor_class IS
    'PROVISIONAL name-pattern donor classifier. Phase 6 replaces this with entity '
    'resolution against TEC lobbyist-employer registrations. Do not present output '
    'derived from this as settled.';


-- --- per-legislator finance summary ------------------------------------------
-- Each aggregate is computed in its own subquery precisely so nothing fans out.

CREATE VIEW v_legislator_finance AS
SELECT
    l.id                AS legislator_id,
    l.full_name_raw     AS legislator,
    l.party,
    l.chamber,
    l.district,
    f.contribution_count,
    f.total_raised,
    f.pac_total,
    f.individual_total,
    CASE WHEN f.total_raised > 0
         THEN round(100.0 * f.pac_total / f.total_raised, 1) END AS pac_share_pct,
    t.top10_total,
    CASE WHEN f.total_raised > 0
         THEN round(100.0 * t.top10_total / f.total_raised, 1) END AS top10_concentration_pct,
    e.total_spent
FROM legislators l
LEFT JOIN LATERAL (
    SELECT count(*)                                        AS contribution_count,
           coalesce(sum(amount), 0)                        AS total_raised,
           coalesce(sum(amount) FILTER (WHERE donor_class(donor_name) = 'pac'), 0)        AS pac_total,
           coalesce(sum(amount) FILTER (WHERE donor_class(donor_name) = 'individual'), 0) AS individual_total
    FROM contributions WHERE recipient_legislator_id = l.id
) f ON true
LEFT JOIN LATERAL (
    SELECT coalesce(sum(s), 0) AS top10_total FROM (
        SELECT sum(amount) AS s FROM contributions
        WHERE recipient_legislator_id = l.id AND donor_name IS NOT NULL
        GROUP BY donor_name ORDER BY 1 DESC NULLS LAST LIMIT 10
    ) d
) t ON true
LEFT JOIN LATERAL (
    SELECT coalesce(sum(amount), 0) AS total_spent
    FROM expenditures WHERE spender_legislator_id = l.id
) e ON true;

COMMENT ON VIEW v_legislator_finance IS
    'One row per legislator. Every aggregate is computed in its own LATERAL so that '
    'money is never multiplied by bill counts (D71).';


-- --- the cross-reference: bills against the money around them -----------------

CREATE FUNCTION f_sponsor_windows(
    lookback_days int DEFAULT 90,
    p_general_assembly int DEFAULT NULL,
    p_legislator_id bigint DEFAULT NULL
)
RETURNS TABLE (
    legislator_id        bigint,
    legislator           text,
    party                text,
    chamber             chamber,
    bill_id              bigint,
    bill_number          text,
    general_assembly     smallint,
    introduced_date      date,
    passed               boolean,
    passed_date          date,
    sponsor_type         sponsor_type,
    pre_intro_total      numeric,
    pre_intro_count      bigint,
    post_pass_same_donor_total numeric
) AS $$
    SELECT
        l.id, l.full_name_raw, l.party, l.chamber,
        b.id, b.bill_number, b.general_assembly, b.introduced_date,
        b.passed, b.passed_date, s.sponsor_type,
        pre.total, pre.cnt, post.total
    FROM sponsorships s
    JOIN bills b       ON b.id = s.bill_id
    JOIN legislators l ON l.id = s.legislator_id
    -- Contributions in the N days before introduction. Computed per bill in its own
    -- scope, so no contribution is ever counted against more than one bill's window
    -- inside a single aggregate.
    LEFT JOIN LATERAL (
        SELECT coalesce(sum(c.amount), 0) AS total, count(*) AS cnt
        FROM contributions c
        WHERE c.recipient_legislator_id = l.id
          AND c.contribution_date >= b.introduced_date - (lookback_days || ' days')::interval
          AND c.contribution_date <  b.introduced_date
    ) pre ON true
    -- Money from the SAME donors after passage: the round-trip that matters more
    -- than raw timing.
    LEFT JOIN LATERAL (
        SELECT coalesce(sum(c2.amount), 0) AS total
        FROM contributions c2
        WHERE b.passed_date IS NOT NULL
          AND c2.recipient_legislator_id = l.id
          AND c2.contribution_date >  b.passed_date
          AND c2.contribution_date <= b.passed_date + (lookback_days || ' days')::interval
          AND c2.donor_name IN (
              SELECT c3.donor_name FROM contributions c3
              WHERE c3.recipient_legislator_id = l.id
                AND c3.donor_name IS NOT NULL
                AND c3.contribution_date >= b.introduced_date - (lookback_days || ' days')::interval
                AND c3.contribution_date <  b.introduced_date
          )
    ) post ON true
    WHERE b.introduced_date IS NOT NULL
      AND (p_general_assembly IS NULL OR b.general_assembly = p_general_assembly)
      AND (p_legislator_id    IS NULL OR l.id = p_legislator_id)
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION f_sponsor_windows IS
    'Cross-reference analysis for ANY legislator (D65: the method must work for '
    'everyone, not one subject). lookback_days is configurable, default 90.';

COMMIT;
