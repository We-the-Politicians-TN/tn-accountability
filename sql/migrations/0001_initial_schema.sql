-- =============================================================================
-- 0001_initial_schema.sql
-- Tennessee Legislator Accountability Platform — initial schema.
--
-- Design rule that applies to every table: the raw source text is preserved
-- alongside any cleaned value. Columns suffixed `_raw` hold exactly what the
-- source published; unsuffixed columns hold the normalized version. When they
-- disagree, the raw column wins as evidence.
--
-- Every row that came from an ingest run carries `data_pull_id` so any figure on
-- the public site can be traced back to the run, the source, and the file.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- Enumerated types
-- -----------------------------------------------------------------------------

CREATE TYPE chamber AS ENUM ('house', 'senate');

CREATE TYPE donor_type AS ENUM ('individual', 'pac', 'business', 'party', 'other', 'unknown');

CREATE TYPE sponsor_type AS ENUM ('primary', 'cosponsor');

CREATE TYPE vote_cast AS ENUM ('yea', 'nay', 'not_voting', 'absent', 'present', 'other');

CREATE TYPE ingest_source AS ENUM (
    'legiscan',
    'accountability_project',
    'tref',
    'tn_ethics_commission'
);


-- -----------------------------------------------------------------------------
-- data_pulls — provenance log. Written first by every ingest run; other tables
-- reference it. Nothing enters the database without a row here.
-- -----------------------------------------------------------------------------

CREATE TABLE data_pulls (
    id              bigserial PRIMARY KEY,
    source          ingest_source NOT NULL,
    started_at      timestamptz   NOT NULL DEFAULT now(),
    finished_at     timestamptz,
    -- 'running' until the job completes; then 'success' or 'failed'.
    status          text          NOT NULL DEFAULT 'running'
                                  CHECK (status IN ('running', 'success', 'failed')),
    rows_added      integer       NOT NULL DEFAULT 0,
    rows_updated    integer       NOT NULL DEFAULT 0,
    rows_skipped    integer       NOT NULL DEFAULT 0,
    -- Paths of the raw files consumed, relative to the repo root. The evidence trail.
    source_files    text[]        NOT NULL DEFAULT '{}',
    -- Free-form detail: API cursor, session id, date range covered, error text.
    notes           text,
    error           text
);

COMMENT ON TABLE data_pulls IS
    'One row per ingest run. Every imported record points back here so any number can be traced to its source file and run.';


-- -----------------------------------------------------------------------------
-- legislators — one row per person who served, current or not.
-- Terms and TREF candidate identities are separate tables because a legislator
-- has many of each.
-- -----------------------------------------------------------------------------

CREATE TABLE legislators (
    id                  bigserial PRIMARY KEY,
    -- LegiScan's stable person identifier. Null for anyone added by hand.
    legiscan_people_id  integer UNIQUE,

    full_name_raw       text NOT NULL,   -- exactly as the source published it
    full_name           text NOT NULL,   -- normalized for matching
    first_name          text,
    middle_name         text,
    last_name           text,
    suffix              text,
    nickname            text,            -- drives Phase 4 name matching

    party               text,
    -- Current/most recent seat. Historical seats live in legislator_terms.
    chamber             chamber,
    district            text,            -- text: TN districts are numeric but keep source form

    ballotpedia_url     text,
    opensecrets_id      text,
    votesmart_id        integer,

    data_pull_id        bigint REFERENCES data_pulls(id),
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX legislators_full_name_idx ON legislators (full_name);
CREATE INDEX legislators_last_name_idx ON legislators (last_name);
CREATE INDEX legislators_chamber_district_idx ON legislators (chamber, district);

COMMENT ON TABLE legislators IS
    'Every person who served in a covered session, not just current members.';


-- -----------------------------------------------------------------------------
-- legislator_terms — terms served, with start/end dates.
-- -----------------------------------------------------------------------------

CREATE TABLE legislator_terms (
    id              bigserial PRIMARY KEY,
    legislator_id   bigint NOT NULL REFERENCES legislators(id) ON DELETE CASCADE,
    chamber         chamber NOT NULL,
    district        text    NOT NULL,
    party           text,
    -- General Assembly number, e.g. 111, 112, 113, 114.
    general_assembly smallint,
    start_date      date NOT NULL,
    end_date        date,            -- null while serving
    data_pull_id    bigint REFERENCES data_pulls(id),

    CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX legislator_terms_legislator_idx ON legislator_terms (legislator_id);
CREATE INDEX legislator_terms_ga_idx ON legislator_terms (general_assembly);


-- -----------------------------------------------------------------------------
-- legislator_tref_ids — a legislator's campaign-finance identities.
-- Populated in Phase 4 by name matching; low-confidence matches stay unapproved
-- until a human signs off, and unapproved rows must not feed any published figure.
-- -----------------------------------------------------------------------------

CREATE TABLE legislator_tref_ids (
    id                  bigserial PRIMARY KEY,
    legislator_id       bigint NOT NULL REFERENCES legislators(id) ON DELETE CASCADE,
    -- TREF's candidate/committee identifier, when the source provides one.
    tref_candidate_id   text,
    -- The filer name as it appears in TREF, e.g. 'Committee to Elect Jane Doe'.
    tref_name_raw       text NOT NULL,
    tref_name           text NOT NULL,

    match_confidence    numeric(5,2) CHECK (match_confidence BETWEEN 0 AND 100),
    match_method        text,        -- e.g. 'exact', 'fuzzy+district', 'manual'
    -- False until a human approves. Analysis views filter on this.
    approved            boolean NOT NULL DEFAULT false,
    approved_by         text,
    approved_at         timestamptz,
    notes               text,

    data_pull_id        bigint REFERENCES data_pulls(id),
    created_at          timestamptz NOT NULL DEFAULT now(),

    UNIQUE (legislator_id, tref_name)
);

CREATE INDEX legislator_tref_ids_name_idx ON legislator_tref_ids (tref_name);
CREATE INDEX legislator_tref_ids_unapproved_idx ON legislator_tref_ids (approved)
    WHERE approved = false;

COMMENT ON COLUMN legislator_tref_ids.approved IS
    'Unapproved matches must never feed a published number. Phase 4 requires human sign-off below 90% confidence.';


-- -----------------------------------------------------------------------------
-- donors — normalized donor entities, built in Phase 6 by clustering the raw
-- donor names found in contributions.
-- -----------------------------------------------------------------------------

CREATE TABLE donors (
    id                  bigserial PRIMARY KEY,
    canonical_name      text NOT NULL UNIQUE,
    donor_type          donor_type NOT NULL DEFAULT 'unknown',
    -- Industry category drives the subject-matched signal (Phase 6).
    industry_category   text,
    industry_source     text,   -- 'lobbyist_employer' | 'pac_name' | 'manual' | 'employer'
    -- True once a human has confirmed the category.
    category_reviewed   boolean NOT NULL DEFAULT false,

    employer            text,
    city                text,
    state               text,

    lobbyist_employer_id bigint,  -- FK added after lobbyist_employers is created
    notes               text,

    data_pull_id        bigint REFERENCES data_pulls(id),
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX donors_industry_idx ON donors (industry_category);
CREATE INDEX donors_type_idx ON donors (donor_type);


-- -----------------------------------------------------------------------------
-- contributions — money in. Recipient may be a legislator or a committee that
-- has not yet been matched to one, so recipient_legislator_id is nullable and
-- the raw recipient text is always kept.
-- -----------------------------------------------------------------------------

CREATE TABLE contributions (
    id                      bigserial PRIMARY KEY,

    contribution_date       date,
    contribution_date_raw   text,
    amount                  numeric(14,2),
    amount_raw              text,

    donor_name_raw          text NOT NULL,
    donor_name              text,
    donor_type              donor_type NOT NULL DEFAULT 'unknown',
    donor_id                bigint REFERENCES donors(id),   -- set in Phase 6

    donor_employer_raw      text,
    donor_employer          text,
    donor_occupation_raw    text,
    donor_occupation        text,
    donor_address_raw       text,
    donor_city              text,
    donor_state             text,
    donor_zip               text,

    recipient_name_raw      text NOT NULL,
    recipient_name          text,
    recipient_legislator_id bigint REFERENCES legislators(id),
    recipient_committee     text,

    -- Provenance: which filing this came out of.
    source_report           text,
    source_report_date      date,
    source_record_id        text,   -- the source's own row identifier, if any
    source_file             text,   -- path under data/raw/

    data_pull_id            bigint NOT NULL REFERENCES data_pulls(id),
    created_at              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX contributions_date_idx ON contributions (contribution_date);
CREATE INDEX contributions_recipient_idx ON contributions (recipient_legislator_id);
CREATE INDEX contributions_donor_idx ON contributions (donor_id);
CREATE INDEX contributions_donor_name_idx ON contributions (donor_name);
-- The core analysis query is "contributions to legislator X between two dates".
CREATE INDEX contributions_recipient_date_idx
    ON contributions (recipient_legislator_id, contribution_date);
-- Guards against double-loading the same source row on re-ingest.
CREATE UNIQUE INDEX contributions_source_dedupe_idx
    ON contributions (source_file, source_record_id)
    WHERE source_record_id IS NOT NULL;


-- -----------------------------------------------------------------------------
-- expenditures — money out.
-- -----------------------------------------------------------------------------

CREATE TABLE expenditures (
    id                      bigserial PRIMARY KEY,

    expenditure_date        date,
    expenditure_date_raw    text,
    amount                  numeric(14,2),
    amount_raw              text,

    vendor_name_raw         text NOT NULL,
    vendor_name             text,
    purpose_raw             text,
    purpose                 text,

    vendor_address_raw      text,
    vendor_city             text,
    vendor_state            text,
    vendor_zip              text,

    -- Who spent the money.
    spender_name_raw        text NOT NULL,
    spender_name            text,
    spender_legislator_id   bigint REFERENCES legislators(id),
    spender_committee       text,

    source_report           text,
    source_report_date      date,
    source_record_id        text,
    source_file             text,

    data_pull_id            bigint NOT NULL REFERENCES data_pulls(id),
    created_at              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX expenditures_date_idx ON expenditures (expenditure_date);
CREATE INDEX expenditures_spender_idx ON expenditures (spender_legislator_id);
CREATE INDEX expenditures_vendor_idx ON expenditures (vendor_name);
CREATE UNIQUE INDEX expenditures_source_dedupe_idx
    ON expenditures (source_file, source_record_id)
    WHERE source_record_id IS NOT NULL;


-- -----------------------------------------------------------------------------
-- bills
-- -----------------------------------------------------------------------------

CREATE TABLE bills (
    id                  bigserial PRIMARY KEY,
    legiscan_bill_id    integer UNIQUE NOT NULL,

    session_name        text,
    general_assembly    smallint,
    session_year_start  smallint,
    bill_number         text NOT NULL,   -- e.g. 'HB0001'
    bill_type           text,            -- bill, resolution, etc.

    title               text,
    description         text,
    -- LegiScan subject labels, kept as published.
    subjects            text[] NOT NULL DEFAULT '{}',
    -- Our own category, assigned in Phase 6, used for subject matching.
    subject_category    text,
    committee           text,

    introduced_date     date,
    last_action         text,
    last_action_date    date,
    status              text,
    status_raw          text,
    passed              boolean NOT NULL DEFAULT false,
    passed_date         date,

    legiscan_url        text,
    state_url           text,

    data_pull_id        bigint REFERENCES data_pulls(id),
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX bills_ga_idx ON bills (general_assembly);
CREATE INDEX bills_introduced_idx ON bills (introduced_date);
CREATE INDEX bills_subject_category_idx ON bills (subject_category);
CREATE INDEX bills_subjects_idx ON bills USING gin (subjects);


-- -----------------------------------------------------------------------------
-- sponsorships
-- -----------------------------------------------------------------------------

CREATE TABLE sponsorships (
    id              bigserial PRIMARY KEY,
    bill_id         bigint NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    legislator_id   bigint NOT NULL REFERENCES legislators(id) ON DELETE CASCADE,
    sponsor_type    sponsor_type NOT NULL,
    sponsor_order   smallint,
    sponsored_date  date,
    data_pull_id    bigint REFERENCES data_pulls(id),

    UNIQUE (bill_id, legislator_id, sponsor_type)
);

CREATE INDEX sponsorships_legislator_idx ON sponsorships (legislator_id);
CREATE INDEX sponsorships_bill_idx ON sponsorships (bill_id);


-- -----------------------------------------------------------------------------
-- roll_calls and votes — a roll call is one recorded vote event on a bill;
-- `votes` holds how each legislator voted in it.
-- -----------------------------------------------------------------------------

CREATE TABLE roll_calls (
    id                    bigserial PRIMARY KEY,
    legiscan_roll_call_id integer UNIQUE NOT NULL,
    bill_id               bigint NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    vote_date             date,
    description           text,
    chamber               chamber,
    yea                   smallint,
    nay                   smallint,
    not_voting            smallint,
    absent                smallint,
    passed                boolean,
    data_pull_id          bigint REFERENCES data_pulls(id)
);

CREATE INDEX roll_calls_bill_idx ON roll_calls (bill_id);

CREATE TABLE votes (
    id              bigserial PRIMARY KEY,
    roll_call_id    bigint NOT NULL REFERENCES roll_calls(id) ON DELETE CASCADE,
    bill_id         bigint NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    legislator_id   bigint NOT NULL REFERENCES legislators(id) ON DELETE CASCADE,
    vote            vote_cast NOT NULL,
    vote_raw        text,
    data_pull_id    bigint REFERENCES data_pulls(id),

    UNIQUE (roll_call_id, legislator_id)
);

CREATE INDEX votes_legislator_idx ON votes (legislator_id);
CREATE INDEX votes_bill_idx ON votes (bill_id);


-- -----------------------------------------------------------------------------
-- lobbyist_employers and their registered lobbyists (TN Ethics Commission).
-- These supply the industry categories that make the subject-matched signal work.
-- -----------------------------------------------------------------------------

CREATE TABLE lobbyist_employers (
    id                  bigserial PRIMARY KEY,
    employer_name_raw   text NOT NULL,
    employer_name       text NOT NULL,
    -- Years the employer appears in a registration file.
    registration_years  smallint[] NOT NULL DEFAULT '{}',
    issue_areas         text[] NOT NULL DEFAULT '{}',
    industry_category   text,
    address_raw         text,
    city                text,
    state               text,
    source_file         text,
    data_pull_id        bigint REFERENCES data_pulls(id),
    created_at          timestamptz NOT NULL DEFAULT now(),

    UNIQUE (employer_name)
);

CREATE INDEX lobbyist_employers_industry_idx ON lobbyist_employers (industry_category);

CREATE TABLE lobbyists (
    id                      bigserial PRIMARY KEY,
    lobbyist_name_raw       text NOT NULL,
    lobbyist_name           text NOT NULL,
    lobbyist_employer_id    bigint REFERENCES lobbyist_employers(id) ON DELETE CASCADE,
    registration_years      smallint[] NOT NULL DEFAULT '{}',
    source_file             text,
    data_pull_id            bigint REFERENCES data_pulls(id)
);

CREATE INDEX lobbyists_employer_idx ON lobbyists (lobbyist_employer_id);

-- Deferred FK: donors is created before lobbyist_employers because contributions
-- depends on donors.
ALTER TABLE donors
    ADD CONSTRAINT donors_lobbyist_employer_fkey
    FOREIGN KEY (lobbyist_employer_id) REFERENCES lobbyist_employers(id);


-- -----------------------------------------------------------------------------
-- updated_at maintenance
-- -----------------------------------------------------------------------------

CREATE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER legislators_updated_at BEFORE UPDATE ON legislators
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER bills_updated_at BEFORE UPDATE ON bills
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER donors_updated_at BEFORE UPDATE ON donors
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
