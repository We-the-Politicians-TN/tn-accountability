-- =============================================================================
-- 0015_data_corrections.sql
--
-- A logged correction to source data, verified against a more authoritative source.
--
-- LegiScan's 114th General Assembly people file lists London Lamar as a House member.
-- The Tennessee General Assembly's own site shows "Senator London Lamar, District 33"
-- (wapp.capitol.tn.gov/apps/legislatorinfo/member.aspx?district=s33, checked
-- 2026-09-21), and the Ethics Commission lists her Statement of Interests under
-- "Senator". LegiScan had her correctly in the Senate for the 113th.
--
-- Corrections are never made by editing a row silently. They are recorded here with
-- the old value, the new value, the source, and who verified it, so the change is as
-- checkable as the data it changes. Raw (_raw) columns are never modified.
-- =============================================================================

BEGIN;

CREATE TABLE data_corrections (
    id            bigserial PRIMARY KEY,
    table_name    text NOT NULL,
    row_id        bigint NOT NULL,
    column_name   text NOT NULL,
    old_value     text,
    new_value     text,
    source_url    text NOT NULL,
    verified_at   date NOT NULL,
    verified_by   text NOT NULL,
    note          text
);
ALTER TABLE data_corrections ENABLE ROW LEVEL SECURITY;
COMMENT ON TABLE data_corrections IS
    'Every deliberate change to ingested data, with old value, new value and the '
    'source that justified it. Raw columns are never changed.';

INSERT INTO data_corrections (table_name, row_id, column_name, old_value, new_value, source_url, verified_at, verified_by, note)
SELECT 'legislators', id, 'chamber', chamber::text, 'senate',
       'https://wapp.capitol.tn.gov/apps/legislatorinfo/member.aspx?district=s33', '2026-09-21', 'build session',
       'LegiScan 114th GA people file says House; capitol.tn.gov and the Ethics Commission say Senator, District 33.'
FROM legislators WHERE full_name_raw = 'London Lamar';
INSERT INTO data_corrections (table_name, row_id, column_name, old_value, new_value, source_url, verified_at, verified_by, note)
SELECT 'legislators', id, 'district', district, '33',
       'https://wapp.capitol.tn.gov/apps/legislatorinfo/member.aspx?district=s33', '2026-09-21', 'build session', NULL
FROM legislators WHERE full_name_raw = 'London Lamar';

UPDATE legislators SET chamber = 'senate', district = '33' WHERE full_name_raw = 'London Lamar';
UPDATE legislator_terms t SET chamber = 'senate', district = '33',
       source = coalesce(source, '') || '; chamber corrected per capitol.tn.gov 2026-09-21'
FROM legislators l WHERE t.legislator_id = l.id AND l.full_name_raw = 'London Lamar' AND t.general_assembly = 114;

COMMIT;
