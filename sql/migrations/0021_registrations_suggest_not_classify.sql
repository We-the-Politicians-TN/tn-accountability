-- =============================================================================
-- 0021_registrations_suggest_not_classify.sql
--
-- "amusement, games, sports" is gaming (the Sports Betting Alliance ticks it), so it
-- maps to the alcohol/tobacco/gaming code rather than hospitality.
--
-- More importantly: automatic donor classification from lobbying registrations is
-- withdrawn. Even for focused filers it ran roughly 40% wrong on the largest cases —
-- the Tennessee Smoke Free Association (a vape-shop trade group) as health care,
-- BusPatrol (a school-bus camera vendor) as education — because a registration says
-- what an employer lobbies ABOUT. From here the registration is shown to the human
-- reviewer as a suggestion beside each donor, and never applied by itself.
-- =============================================================================
BEGIN;
UPDATE lobby_subject_category_map SET category = 'alcohol_gaming', reviewed = false
WHERE subject = 'amusement, games, sports';
DELETE FROM donor_category_map WHERE assigned_by = 'ss8011' AND NOT reviewed;
COMMIT;
