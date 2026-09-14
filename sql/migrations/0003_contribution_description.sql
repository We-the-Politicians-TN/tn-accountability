-- =============================================================================
-- 0003_contribution_description.sql
--
-- TREF's contributions export carries a "Description" column, used mainly to
-- describe in-kind contributions ("catering", "printing", "office space"). The
-- initial schema had no home for it, which would have meant dropping a published
-- field on load.
--
-- It matters beyond completeness: for in-kind contributions the description is
-- often the only statement of what was actually provided.
-- =============================================================================

BEGIN;

ALTER TABLE contributions
    ADD COLUMN description_raw text,
    ADD COLUMN description     text;

COMMENT ON COLUMN contributions.description_raw IS
    'TREF "Description" — for in-kind contributions, often the only record of what was given.';

COMMIT;
