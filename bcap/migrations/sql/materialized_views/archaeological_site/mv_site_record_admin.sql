-- GENERATED - edit as_spec.py and re-run generate.py. Do not hand-edit.
-- Graph cef9c510-e3e6-4057-ac08-89ad926180b4
-- Requires 00_arches_util.sql (arches_util helpers) to be applied first.
--
-- Reads public.tiles DIRECTLY. The generated archaeological_site.* views are NOT used:
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

CREATE SCHEMA IF NOT EXISTS archaeological_site;

-- ---------------------------------------------------------------------
-- site_record_admin  (cardinality n)
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_site_record_admin CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_site_record_admin AS
WITH site_record_admin AS (
    SELECT t.resourceinstanceid AS resourceinstanceid,
           jsonb_agg(jsonb_build_object(
            'bcap_submission_status', arches_util.reference_flat(t.tiledata -> '167e3e88-98a3-11ee-a464-080027b7463b'),
            'restricted', NULLIF(t.tiledata ->> 'dc974e68-8f0f-11ee-85a0-080027b7463b', '')::boolean
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '0684fec8-0d07-11ed-8804-5254008afee6'::uuid
    GROUP BY t.resourceinstanceid
)
SELECT resourceinstanceid, arr AS site_record_admin FROM site_record_admin;

CREATE UNIQUE INDEX mv_site_record_admin_pk ON archaeological_site.mv_site_record_admin (resourceinstanceid);
