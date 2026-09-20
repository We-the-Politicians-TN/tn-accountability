-- =============================================================================
-- 0009_subject_matching.sql — Phase 6 foundations
--
-- Two additions, both prerequisites for the subject-matched signal that Phase 5
-- showed is the only usable one (D73).
--
-- 1. CEREMONIAL BILLS ARE MARKED AND EXCLUDABLE.
--    Memorial resolutions honour retiring teachers and winning ball teams. They
--    carry no policy content, so pairing one with a donor's industry is meaningless
--    and publishing such a pairing about a named legislator would be indefensible.
--    They are also not rare: 92% of joint resolutions and 95% of simple resolutions
--    in the 114th GA are memorials, and 36% of Johnny Garrett's primary
--    sponsorships. Counting them inflates apparent legislative activity by ~60%
--    (chamber mean 68.9 sponsorships -> 43.0 substantive).
--
-- 2. A SHARED INDUSTRY TAXONOMY.
--    Bill subjects and donor industries must resolve to the SAME vocabulary or they
--    cannot be matched. Both mappings live in tables rather than in code so they can
--    be reviewed, corrected by a human, and cited on the methodology page.
-- =============================================================================

BEGIN;

-- --- ceremonial classification -----------------------------------------------

ALTER TABLE bills ADD COLUMN is_ceremonial boolean;

UPDATE bills SET is_ceremonial = EXISTS (
    SELECT 1 FROM unnest(subjects) s
    WHERE s ILIKE 'Memorials%' OR s ILIKE '%Recognition%'
);

ALTER TABLE bills ALTER COLUMN is_ceremonial SET DEFAULT false;
CREATE INDEX bills_ceremonial_idx ON bills (is_ceremonial);

COMMENT ON COLUMN bills.is_ceremonial IS
    'Memorial/recognition resolution with no policy content. EXCLUDE from every '
    'analysis and from published sponsorship counts: pairing a memorial with donor '
    'money is meaningless, and 92-95% of resolutions are ceremonial.';


-- --- shared industry taxonomy -------------------------------------------------

CREATE TABLE industry_categories (
    code        text PRIMARY KEY,
    label       text NOT NULL,
    description text
);

INSERT INTO industry_categories (code, label, description) VALUES
 ('healthcare',    'Health care',              'Hospitals, physicians, TennCare, pharma, long-term care'),
 ('insurance',     'Insurance',                'Health, property, casualty and title insurers'),
 ('finance',       'Banking and finance',      'Banks, credit unions, consumer lending, investment'),
 ('real_estate',   'Real estate',              'Realtors, developers, property management, homebuilders'),
 ('construction',  'Construction',             'Contractors, highway and heavy construction, materials'),
 ('energy',        'Energy and utilities',     'Electric, gas, water, pipelines, fuel'),
 ('telecom_tech',  'Telecom and technology',   'Broadband, wireless, software, data centres'),
 ('education',     'Education',                'K-12, higher education, charter schools, teachers'),
 ('legal',         'Legal',                    'Trial lawyers, defence bar, legal services'),
 ('agriculture',   'Agriculture',              'Farming, forestry, farm bureau, agribusiness'),
 ('transport',     'Transportation',           'Trucking, rail, air, automotive dealers, logistics'),
 ('hospitality',   'Retail and hospitality',   'Restaurants, hotels, retail, grocery'),
 ('labor',         'Labor',                    'Unions and labour organisations'),
 ('alcohol_gaming','Alcohol, tobacco, gaming', 'Beer, wine, spirits, tobacco, vaping, lottery'),
 ('firearms',      'Firearms',                 'Firearms manufacture, retail, sporting associations'),
 ('manufacturing', 'Manufacturing',            'Industrial and consumer goods manufacture'),
 ('party_caucus',  'Party and caucus',         'Party committees and legislative caucus funds'),
 ('other',         'Other or uncategorised',   'Not yet assigned to an industry');

-- LegiScan subject label -> industry. Many-to-one: a bill may carry several subjects.
CREATE TABLE subject_category_map (
    subject     text PRIMARY KEY,
    category    text NOT NULL REFERENCES industry_categories(code),
    assigned_by text NOT NULL DEFAULT 'rule',
    reviewed    boolean NOT NULL DEFAULT false,
    notes       text
);

-- Donor entity -> industry. Populated by Phase 6 clustering, corrected by a human.
CREATE TABLE donor_category_map (
    donor_name  text PRIMARY KEY,
    category    text NOT NULL REFERENCES industry_categories(code),
    confidence  numeric(5,2),
    assigned_by text NOT NULL DEFAULT 'rule',
    reviewed    boolean NOT NULL DEFAULT false,
    notes       text
);

CREATE INDEX donor_category_map_cat_idx ON donor_category_map (category);
CREATE INDEX subject_category_map_cat_idx ON subject_category_map (category);

COMMENT ON TABLE donor_category_map IS
    'Donor -> industry assignments. `reviewed` records human confirmation. Unreviewed '
    'assignments are usable for exploration but must be labelled provisional wherever '
    'they reach a reader.';

COMMIT;
