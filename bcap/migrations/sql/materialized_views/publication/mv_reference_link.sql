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
-- reference_link  (cardinality 1)
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS publication.mv_reference_link CASCADE;
CREATE MATERIALIZED VIEW publication.mv_reference_link AS
WITH reference_link AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'archaeological_sites', arches_util.resource_ids(t.tiledata -> '20c23f8a-be00-11ed-bdf6-5254004d77d3'),
            'site_visits', arches_util.resource_ids(t.tiledata -> '10517634-be00-11ed-b38b-5254004d77d3'),
            'repositories', arches_util.resource_ids(t.tiledata -> '68b9813a-be01-11ed-8b5e-5254004d77d3')
        ) AS obj
    FROM public.tiles t
    WHERE t.nodegroupid = '037c8f98-be00-11ed-8b5e-5254004d77d3'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS reference_link FROM reference_link;

CREATE UNIQUE INDEX mv_reference_link_pk ON publication.mv_reference_link (resourceinstanceid);
