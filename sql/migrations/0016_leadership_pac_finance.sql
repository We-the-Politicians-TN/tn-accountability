-- =============================================================================
-- 0016_leadership_pac_finance.sql
--
-- Money raised by the leadership PACs members declare on their Statements of
-- Interests (Q15). The declared name keys to the TREF filer name exactly once
-- punctuation and spaces are stripped: "JACK PAC" -> "JACK - PAC", "BOW-PAC" ->
-- "BOWPAC" and "BOW-PAC". Tested against the first 18 declarations: 18 matched.
--
-- This is kept SEPARATE from the member's own totals and must never be added to
-- them. A leadership PAC is a distinct committee the member controls; showing it
-- beside their campaign figures, labelled, is accurate. Folding it in would not be.
-- =============================================================================

BEGIN;

CREATE VIEW v_leadership_pac_finance AS
WITH keys AS (
    SELECT DISTINCT legislator_id, legislator, pac_name_raw, pac_key FROM v_leadership_pacs
),
tref AS (
    SELECT upper(regexp_replace(recipient_name, '[^A-Za-z0-9]', '', 'g')) AS key,
           recipient_name, count(*) AS n, sum(amount) AS total,
           min(contribution_date) AS first_date, max(contribution_date) AS last_date
    FROM contributions WHERE recipient_name IS NOT NULL
    GROUP BY 1, 2
)
SELECT k.legislator_id, k.legislator, k.pac_name_raw, k.pac_key,
       array_agg(t.recipient_name ORDER BY t.recipient_name) AS tref_names,
       sum(t.n)::bigint AS contributions, sum(t.total) AS total_raised,
       min(t.first_date) AS first_date, max(t.last_date) AS last_date
FROM keys k JOIN tref t ON t.key = k.pac_key
GROUP BY 1, 2, 3, 4;

COMMENT ON VIEW v_leadership_pac_finance IS
    'Contributions to each member''s declared leadership PAC. Never add these to the '
    'member''s own campaign totals; display beside them, labelled.';

COMMIT;
