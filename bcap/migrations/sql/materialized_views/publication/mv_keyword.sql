-- GENERATED - edit pub_spec.py and re-run generate.py. Do not hand-edit.
-- Graph 3caf329f-b8f7-11e6-84a5-026d961c88e6
-- Requires 00_arches_util.sql (arches_util helpers) to be applied first.
--
-- Reads public.tiles DIRECTLY. The generated publication.* views are NOT used:
-- each LEFT JOINs edit_log twice with a text->uuid cast that no index can serve.
--
-- INVARIANTS (downstream depends on these - do not change silently):
--   * every key ALWAYS present; empty means null, never absent. No jsonb_strip_nulls.
--   * cardinality-n children are ALWAYS a jsonb array, [] when empty, never null.
--   * cardinality-1 branches are an object, or null when the tile does not exist.
--   * array order is tiles.sortorder, then tileid. Stable across refreshes.

SET client_min_messages = warning;   -- ST_MakeValid emits a NOTICE per repair
SET maintenance_work_mem = '512MB';
SET work_mem             = '128MB';

CREATE SCHEMA IF NOT EXISTS publication;

-- ---------------------------------------------------------------------
-- keyword  (cardinality n)
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS publication.mv_keyword CASCADE;
CREATE MATERIALIZED VIEW publication.mv_keyword AS
WITH keyword AS (
    SELECT t.resourceinstanceid AS resourceinstanceid,
           jsonb_agg(jsonb_build_object(
            'keyword', arches_util.reference_flat(t.tiledata -> 'b5f5b1ed-e74a-11e6-84a6-026d961c88e6')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'b5f5b1ed-e74a-11e6-84a6-026d961c88e6'::uuid
    GROUP BY t.resourceinstanceid
)
SELECT resourceinstanceid, arr AS keyword FROM keyword;

CREATE UNIQUE INDEX mv_keyword_pk ON publication.mv_keyword (resourceinstanceid);
