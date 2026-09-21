-- =============================================================================
-- 0019_employer_industry_source.sql
--
-- iLobby's subject matters describe what an employer lobbies ABOUT, not what it
-- IS. "economic & industrial development", "labor", "taxation" and "crime & criminal
-- procedure" are issues nearly any company can tick; mapping them to industries made
-- BNSF Railway "manufacturing" and Belz Investco "legal". Only subjects that name an
-- industry may classify an employer; issue subjects map to 'other' on purpose, and
-- the employer's NAME is the fallback (the same rules that classify donors).
--
-- Every employer records where its industry came from, so a donor is overridden
-- only by a declared industry, never by a second name-pattern guess.
-- =============================================================================

BEGIN;

ALTER TABLE lobbyist_employers ADD COLUMN industry_source text;
COMMENT ON COLUMN lobbyist_employers.industry_source IS
    '''declared_subject'' = from an industry-type subject the employer itself listed; '
    '''name_pattern'' = fallback from the employer''s name. Only the former overrides donors.';

UPDATE lobby_subject_category_map SET category = 'other', reviewed = false
WHERE subject IN (
  'abortion', 'alcoholism & abuse', 'business & commerce', 'charitable & nonprofit organizations',
  'consumer protection', 'corporations & associations', 'corrections', 'crime & criminal procedure',
  'disaster preparedness & relief', 'economic & industrial development', 'elections',
  'environment/public lands', 'family issues', 'fees & other non-tax revenue', 'immigration', 'labor',
  'law enforcement', 'local government & special districts',
  'mental health & intellectual/developmental disabilities', 'occupational regulation',
  'parks & wildlife', 'safety', 'state agencies, boards, & commissions',
  'state employees, officers, & symbols', 'state finances', 'taxation', 'tort reform', 'water',
  'workers'' compensation');

-- What remains classifies: agriculture, alcoholic beverage regulation, amusement/games/sports,
-- communications & press, education, financial institutions, health & health care,
-- hospitals & health care providers, insurance, oil & gas, property interests,
-- tenn care & cover tennessee, tourism, transportation, utilities/common carriers.

COMMIT;
