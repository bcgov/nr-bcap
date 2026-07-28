-- GENERATED - edit sv_spec.py and re-run generate.py. Do not hand-edit.
-- Graph 2da1c15f-1ab6-4122-9dbc-d10da693ac79
-- Requires 00_arches_util.sql (arches_util helpers) to be applied first.
--
-- Reads public.tiles DIRECTLY. The generated site_visit.* views are NOT used:
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

CREATE SCHEMA IF NOT EXISTS site_visit;

-- ---------------------------------------------------------------------
-- ancestral_remains  (cardinality n)
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_ancestral_remains CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_ancestral_remains AS
WITH ancestral_remains AS (
    SELECT t.resourceinstanceid AS resourceinstanceid,
           jsonb_agg(jsonb_build_object(
            'ancestral_remains_type', arches_util.reference_flat(t.tiledata -> '6f96fb9a-5049-11f0-91cd-0242ac170006'),
            'ancestral_remains_status', arches_util.reference_flat(t.tiledata -> '6f96fd5c-5049-11f0-91cd-0242ac170006'),
            'ancestral_remains_remarks', arches_util.i18n_text(t.tiledata -> '6f96fe2e-5049-11f0-91cd-0242ac170006'),
            'ancestral_remains_repository', arches_util.resource_id(t.tiledata -> 'a87dd01e-5ce2-11f0-a419-0242ac170007'),
            'minimum_number_of_individuals', NULLIF(t.tiledata ->> '6f96fef6-5049-11f0-91cd-0242ac170006', '')::numeric,
            'multiple_burials', NULLIF(t.tiledata ->> '6f96fc94-5049-11f0-91cd-0242ac170006', '')::boolean
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '6f96f910-5049-11f0-91cd-0242ac170006'::uuid
    GROUP BY t.resourceinstanceid
)
SELECT resourceinstanceid, arr AS ancestral_remains FROM ancestral_remains;

CREATE UNIQUE INDEX mv_ancestral_remains_pk ON site_visit.mv_ancestral_remains (resourceinstanceid);
