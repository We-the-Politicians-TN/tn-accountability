-- =============================================================================
-- 0020_subject_map_property_carriers.sql
--
-- Two more iLobby subjects stop classifying employers, because they describe an
-- issue rather than an industry:
--   * "property interests": railroads, aggregates firms and a private-prison
--     operator all tick it (they own land). Norfolk Southern, Rogers Group and
--     CoreCivic were all gap-filled as real estate.
--   * "utilities/common carriers": a railroad is a common carrier and an electric
--     co-op is a utility; one subject, two industries.
-- Recorded as a migration so the change to the map is as auditable as the data.
-- =============================================================================
BEGIN;
UPDATE lobby_subject_category_map SET category = 'other', reviewed = false
WHERE subject IN ('property interests', 'utilities/common carriers');
COMMIT;
