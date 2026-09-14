-- =============================================================================
-- 0004_allow_missing_names.sql
--
-- The initial schema assumed every financial record names its counterparty:
-- `vendor_name_raw`, `donor_name_raw`, `recipient_name_raw` and `spender_name_raw`
-- were all NOT NULL. Real TREF filings do not honour that. A 2026 filing by
-- John Rose reports $11,000 for "PROFESSIONAL SERVICES" with the vendor field
-- empty, and the load failed on it.
--
-- Substituting a placeholder would fabricate data. Preserving what an agency
-- published includes preserving what it left blank — and a five-figure payment
-- with no payee named is itself worth being able to see and count.
--
-- Analysis views must therefore treat a missing counterparty as a real category,
-- not assume it away.
-- =============================================================================

BEGIN;

ALTER TABLE expenditures  ALTER COLUMN vendor_name_raw    DROP NOT NULL;
ALTER TABLE expenditures  ALTER COLUMN spender_name_raw   DROP NOT NULL;
ALTER TABLE contributions ALTER COLUMN donor_name_raw     DROP NOT NULL;
ALTER TABLE contributions ALTER COLUMN recipient_name_raw DROP NOT NULL;

COMMENT ON COLUMN expenditures.vendor_name_raw IS
    'As published by TREF. Nullable: some filings report an amount and purpose '
    'with no payee named. Do not substitute a placeholder.';

COMMIT;
