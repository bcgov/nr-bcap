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
-- archaeological_data  (cardinality 1)  children: site_typology
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_archaeological_data CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_archaeological_data AS
WITH site_typology AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'typology_class', arches_util.reference_flat(t.tiledata -> '4d3bb20c-01c0-11f0-97f7-0242ac170007'),
            'typology_remark', arches_util.i18n_text(t.tiledata -> 'e3f0d066-62d1-11f0-8725-76ff5c50888d')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '3083c10e-01c0-11f0-97f7-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
archaeological_data AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'site_typology', COALESCE(site_typology.arr, '[]'::jsonb)
        ) AS obj
    FROM public.tiles t
    LEFT JOIN site_typology site_typology ON site_typology.parenttileid = t.tileid
    WHERE t.nodegroupid = '09856d8c-01c0-11f0-97f7-0242ac170007'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS archaeological_data FROM archaeological_data;

CREATE UNIQUE INDEX mv_archaeological_data_pk ON archaeological_site.mv_archaeological_data (resourceinstanceid);
