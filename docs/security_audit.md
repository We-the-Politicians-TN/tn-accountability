# Security audit — Supabase and Postgres

Last run: 2026-09-20. Re-run the SQL checks after any migration that creates tables.

## Threat model for this project

The data is all public record, so **confidentiality is not the main concern**. What
matters is:

1. **Integrity** — the site publishes claims about named public officials. If someone
   altered a contribution amount or a vote, the claims built on it become false while
   still looking sourced. This is the risk that matters most.
2. **Availability** — a wiped or paused database takes the site down.
3. **Credential hygiene** — the service-role key bypasses all RLS. Leaking it is the
   one confidentiality failure that would matter, because it grants write access.

**Disaster recovery is already strong and is worth stating plainly:** the database is
fully reproducible from `data/raw/` plus the migrations and loaders. If the database
were destroyed tomorrow, it could be rebuilt without contacting any agency. Keep
`data/raw/` backed up somewhere off this machine — that, not the database, is the
irreplaceable asset.

## Findings, 2026-09-20

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | `anon`/`authenticated` held `TRUNCATE` on all 14 tables; **RLS does not restrict TRUNCATE** | High (not currently reachable) | **FIXED** — migration 0006 |
| 2 | Default ACL re-granted `TRUNCATE`/`REFERENCES`/`TRIGGER` on every new table | High (recurring) | **FIXED** — migration 0006 |
| 3 | RLS enabled on all tables with **zero policies** = deny-all | Correct, but see below | Accepted |
| 4 | Ingest connects as `postgres` (CREATEROLE, CREATEDB, **BYPASSRLS**) | Medium | Open |
| 5 | Account MFA | — | Done by user |
| 6 | TLS 1.3 in use on the pooler connection | — | Verified OK |

### On finding 3 — this will bite in Phase 8

RLS on with no policies means **deny all**. The public site using the anon key will
read nothing. That is the right default, but it means read access must be granted
deliberately:

- Grant `SELECT` only on the specific tables or views the site actually renders —
  ideally on purpose-built views, not base tables.
- Add an explicit permissive `SELECT` policy for `anon` on those objects.
- Never grant `INSERT`/`UPDATE`/`DELETE`/`TRUNCATE` to `anon`.
- `legislator_tref_ids` must never be readable with `approved = false` rows exposed
  as if confirmed. Prefer a view that filters to `approved = true`.

Do **not** fix a blank page in Phase 8 by loosening migration 0006.

### On finding 4 — a dedicated ingest role

`postgres` has BYPASSRLS, so ingest code silently ignores every policy. A dedicated
role with `INSERT`/`UPDATE`/`SELECT` on the ingest tables and nothing else would mean
a bug in a loader cannot drop a table or alter the schema. Worth doing before the
ingest runs unattended on GitHub Actions (Phase 7), because that is the point at which
the credential lives somewhere other than this laptop.

## Dashboard checklist (cannot be verified from SQL)

- [ ] **Advisors → Security** — run Supabase's own lints and clear anything it flags.
- [ ] **Settings → Database → SSL enforcement** — require SSL for all connections.
- [ ] **Settings → Database → Network restrictions** (Pro) — consider restricting by IP.
      Note the tension: GitHub Actions runners have dynamic IPs, so enabling this may
      break Phase 7 unless the job runs from a fixed-IP host.
- [ ] **Settings → API** — confirm the `service_role` key has never been committed,
      pasted into a client bundle, or shared. Rotate if in any doubt.
- [ ] **Disable unused services** — Auth, Storage, Realtime and Edge Functions are all
      attack surface this project does not currently use.
- [ ] **Backups** — Pro includes daily backups. PITR is a paid add-on and is probably
      unnecessary here given the raw files can rebuild everything.
- [ ] **Off-machine backup of `data/raw/`** — the genuinely irreplaceable asset.

## Re-running the SQL checks

The audit queries live in this session's history; the important recurring one is:

```sql
-- Anything other than zero rows here means a new table leaked privileges to anon.
SELECT grantee, privilege_type, count(*)
FROM information_schema.role_table_grants
WHERE table_schema='public' AND grantee IN ('anon','authenticated')
GROUP BY 1,2;

-- Every table should have rls = true.
SELECT c.relname, c.relrowsecurity
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relkind='r' AND NOT c.relrowsecurity;
```
