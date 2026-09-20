-- =============================================================================
-- 0006_revoke_anon_destructive.sql
--
-- Supabase grants anon and authenticated TRUNCATE, REFERENCES and TRIGGER on every
-- table in `public`, and the default ACL re-grants them on each new table.
--
-- Row Level Security does NOT restrict TRUNCATE — RLS covers SELECT, INSERT,
-- UPDATE and DELETE only. So "RLS is on everywhere" does not prevent an anon-
-- reachable code path from emptying a table.
--
-- Not exploitable today: anon cannot log in directly and PostgREST exposes no
-- TRUNCATE. It becomes reachable as soon as a database function callable by anon
-- exists, which Phases 8 and 9 are likely to add. For a project whose entire value
-- rests on the data being unaltered, this is worth closing before then rather than
-- after.
--
-- This revokes the privileges AND changes the default so future migrations do not
-- silently reintroduce them.
--
-- Read access for the public site is deliberately NOT granted here. Phase 8 should
-- grant SELECT explicitly, on the specific tables or views the site needs, with an
-- accompanying RLS policy — not by loosening this.
-- =============================================================================

BEGIN;

REVOKE TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM anon;
REVOKE TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM authenticated;

-- Stop the default ACL from re-granting them on tables created later.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE TRUNCATE, REFERENCES, TRIGGER ON TABLES FROM anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE TRUNCATE, REFERENCES, TRIGGER ON TABLES FROM authenticated;

COMMIT;
