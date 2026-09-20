-- =============================================================================
-- 0007_drop_row_dedupe_indexes.sql
--
-- Drops the per-row unique indexes on (source_file, source_record_id).
--
-- They were costing far more than they were worth. At 371k contribution rows the
-- index was already 111 MB — versus 3-10 MB for every other index on the table —
-- because it is a unique index over two text columns where `source_file` is a
-- ~70-character path repeated on every row. Extrapolated to the full backfill it
-- would exceed 600 MB by itself, and its maintenance during COPY was the dominant
-- source of write-ahead log volume, which is what actually filled the disk.
--
-- It is also redundant. Loading works on whole (search_type, year) slices tracked
-- in `data_pulls`, and each slice loads inside a single transaction that rolls back
-- on failure, so a half-loaded slice cannot exist. Re-running a loaded slice is
-- skipped; `--replace` deletes the slice first. The row-level guarantee was already
-- provided at the slice level.
--
-- The `source_file` and `source_record_id` COLUMNS remain. Provenance is untouched:
-- every row still names the exact file and line it came from. Only the index goes.
-- =============================================================================

BEGIN;

DROP INDEX IF EXISTS contributions_source_dedupe_idx;
DROP INDEX IF EXISTS expenditures_source_dedupe_idx;

COMMIT;
