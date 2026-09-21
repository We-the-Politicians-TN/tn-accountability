-- =============================================================================
-- 0014_statements_of_interest.sql — Phase 11A
--
-- Statements of Disclosure of Interests (form SS-8004), filed annually by every
-- member of the General Assembly under penalty of perjury (TCA § 8-50-501 ff.).
-- This is the ONLY per-member channel Tennessee publishes for outside income,
-- directorships, investments, sponsored travel, lobbying ties, retainers and
-- leadership PACs. Findings and legal frame: docs/influence_channels.md.
--
-- Same rules as everywhere else. Every item keeps its raw text. Every filing keeps
-- the file it was parsed from and that file's hash. A filing is attributed to a
-- legislator only after the name match is approved — an unapproved match counts
-- for no one (D8, D69). Amended filings supersede originals for the same year.
-- =============================================================================

BEGIN;

CREATE TABLE disclosures (
    id                bigserial PRIMARY KEY,
    tec_filer_id      integer     NOT NULL,       -- the Commission's id for the person
    tec_form_id       integer     NOT NULL,       -- 'f' in the view URL: one per filing
    version           smallint    NOT NULL DEFAULT 1,
    form              text        NOT NULL,       -- 'SS-8004' (members) / 'SS-8005'
    amended           boolean     NOT NULL DEFAULT false,
    report_year       smallint    NOT NULL,
    filer_name_raw    text        NOT NULL,
    filer_name        text        NOT NULL,       -- normalised for matching
    position_raw      text,                       -- 'Representative' / 'Senator'
    chamber           chamber,                    -- derived from position_raw
    address_raw       text,
    filed_date        date,
    is_candidate      boolean,
    -- attribution, mirroring legislator_tref_ids
    legislator_id     bigint REFERENCES legislators(id),
    match_confidence  numeric(5,2),
    match_method      text,
    approved          boolean     NOT NULL DEFAULT false,
    approved_by       text,
    approved_at       timestamptz,
    -- provenance
    source_file       text        NOT NULL,
    sha256            text        NOT NULL,
    source_url        text,
    data_pull_id      bigint      NOT NULL REFERENCES data_pulls(id),
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tec_form_id, version)
);
CREATE INDEX disclosures_filer_year_idx ON disclosures (tec_filer_id, report_year);
CREATE INDEX disclosures_legislator_idx ON disclosures (legislator_id);
CREATE INDEX disclosures_unapproved_idx ON disclosures (approved) WHERE NOT approved;

COMMENT ON TABLE disclosures IS
    'One row per SS-8004/8005 filing version. Attribute to a legislator only when '
    'approved; unapproved filings must not feed any published figure.';

CREATE TABLE disclosure_items (
    id              bigserial PRIMARY KEY,
    disclosure_id   bigint NOT NULL REFERENCES disclosures(id) ON DELETE CASCADE,
    section         text   NOT NULL,   -- 'Sources of Income', 'Legislative Expenses', ...
    part            text,              -- 'A' / 'B' where the form has parts
    seq             smallint NOT NULL,
    lines_raw       text   NOT NULL,   -- the item's lines as published, ' | '-joined
    name            text,              -- line 1: source / organisation / lender / PAC
    detail          text,              -- line 2: address, dates, position, terms
    qualifier       text,              -- 'Income received by: Spouse', 'Held by: Filer'
    amount          numeric(14,2)      -- parsed where the section carries an amount
);
CREATE INDEX disclosure_items_disclosure_idx ON disclosure_items (disclosure_id);
CREATE INDEX disclosure_items_section_idx ON disclosure_items (section);
CREATE INDEX disclosure_items_name_idx ON disclosure_items (name);

COMMENT ON COLUMN disclosure_items.lines_raw IS
    'Exactly as published, so the parsed columns can always be checked against it.';

-- Keep the deny-all posture from the security audit for anything new (D54/D55).
ALTER TABLE disclosures      ENABLE ROW LEVEL SECURITY;
ALTER TABLE disclosure_items ENABLE ROW LEVEL SECURITY;

-- Leadership PACs a member has declared (Q15). Joins the disclosure world to the
-- campaign-finance world by name: "GARRETTPAC" here, "GARRETT PAC" in TREF.
CREATE VIEW v_leadership_pacs AS
SELECT d.legislator_id, l.full_name_raw AS legislator, d.report_year,
       i.name AS pac_name_raw, upper(regexp_replace(i.name, '[^A-Za-z0-9]', '', 'g')) AS pac_key
FROM disclosure_items i
JOIN disclosures d ON d.id = i.disclosure_id
JOIN legislators l ON l.id = d.legislator_id
WHERE i.section = 'Leadership PACs' AND d.approved AND i.name IS NOT NULL;

COMMENT ON VIEW v_leadership_pacs IS
    'Declared leadership PACs per member. pac_key strips spaces/punctuation so '
    '"GARRETTPAC" matches TREF''s "GARRETT PAC" deliberately rather than by fuzzy guess.';

COMMIT;
