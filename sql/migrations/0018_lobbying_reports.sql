-- =============================================================================
-- 0018_lobbying_reports.sql — Phase 11C
--
-- Lobbying Expenditure Reports (SS-8011) and registrations from iLobby. Their
-- value here is the employer's self-declared "nature of business" as subject
-- matters: the authoritative employer -> industry map that replaces name-pattern
-- guessing for every donor that is a registered employer of lobbyists (D80, D95).
--
-- Dollar figures on these reports are RANGES, and there is no per-legislator
-- detail. They are stored as the ranges published, never as a midpoint.
-- =============================================================================

BEGIN;

CREATE TABLE lobbying_reports (
    id                      bigserial PRIMARY KEY,
    report_id               integer NOT NULL UNIQUE,     -- iLobby reportId
    employer_id             integer NOT NULL,            -- iLobby employerId
    lobbyist_employer_id    bigint REFERENCES lobbyist_employers(id),
    period_label            text,                        -- 'Mid Year 2025', 'End Year 2025', 'current'
    report_year             smallint,
    employer_name_raw       text,
    nature_of_business_raw  text,
    subjects                text[] NOT NULL DEFAULT '{}',
    compensation_range_raw  text,                        -- '$350,000 - $400,000'
    expenses_range_raw      text,                        -- 'Less than $10,000'
    in_state_events_raw     text,
    ceo_raw                 text,
    cfo_raw                 text,
    source_file             text NOT NULL,
    sha256                  text,
    data_pull_id            bigint NOT NULL REFERENCES data_pulls(id)
);
CREATE INDEX lobbying_reports_employer_idx ON lobbying_reports (employer_id);
ALTER TABLE lobbying_reports ENABLE ROW LEVEL SECURITY;

ALTER TABLE lobbyist_employers ADD COLUMN ilobby_employer_id integer UNIQUE;
ALTER TABLE lobbyists          ADD COLUMN ilobby_lobbyist_id integer;

-- iLobby's ~48 subject matters -> our industry vocabulary. Reviewable; a human can
-- flip `reviewed` and change a code. Generic subjects map to 'other' on purpose.
CREATE TABLE lobby_subject_category_map (
    subject   text PRIMARY KEY,
    category  text NOT NULL REFERENCES industry_categories(code),
    reviewed  boolean NOT NULL DEFAULT false
);
INSERT INTO lobby_subject_category_map (subject, category) VALUES
 ('abortion','healthcare'),('agriculture','agriculture'),
 ('alcoholic beverage regulation','alcohol_gaming'),('alcoholism & abuse','healthcare'),
 ('amusement, games, sports','hospitality'),('business & commerce','other'),
 ('charitable & nonprofit organizations','other'),('communications & press','telecom_tech'),
 ('consumer protection','other'),('corporations & associations','other'),
 ('corrections','legal'),('crime & criminal procedure','legal'),
 ('disaster preparedness & relief','other'),('economic & industrial development','manufacturing'),
 ('education','education'),('elections','party_caucus'),('environment/public lands','energy'),
 ('family issues','other'),('fees & other non-tax revenue','finance'),
 ('financial institutions','finance'),('health & health care','healthcare'),
 ('hospitals & health care providers','healthcare'),('immigration','other'),
 ('insurance','insurance'),('labor','labor'),('law enforcement','legal'),
 ('local government & special districts','other'),
 ('mental health & intellectual/developmental disabilities','healthcare'),
 ('occupational regulation','other'),('oil & gas','energy'),('parks & wildlife','agriculture'),
 ('property interests','real_estate'),('safety','other'),
 ('state agencies, boards, & commissions','other'),('state employees, officers, & symbols','other'),
 ('state finances','finance'),('taxation','finance'),('tenn care & cover tennessee','healthcare'),
 ('tort reform','legal'),('tourism','hospitality'),('transportation','transport'),
 ('utilities/common carriers','energy'),('water','energy'),('workers'' compensation','insurance');

COMMIT;
