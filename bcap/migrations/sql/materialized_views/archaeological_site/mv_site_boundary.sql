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
-- site_boundary  (cardinality 1)  children: unprotected_areas
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_site_boundary CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_site_boundary AS
WITH geom_unprotected_areas AS (
    SELECT gg.tileid, ST_Collect(ST_Transform(gg.geom, 4326)) AS geom
    FROM public.geojson_geometries gg
    WHERE gg.nodeid = '7c8eb1f8-44e2-4239-afaa-9cbf1fadf160'::uuid
    GROUP BY gg.tileid
),
unprotected_areas AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'unprotected_areas', CASE WHEN g.geom IS NULL THEN NULL ELSE ST_AsGeoJSON(g.geom, 7)::jsonb END,
            'unprotected_area_type', arches_util.reference_flat(t.tiledata -> 'e1f8bec7-9d0c-4f04-9dc8-718d05444105'),
            'other_unprotected_area_type', arches_util.i18n_text(t.tiledata -> '56c7c419-e31c-4e7d-a99a-8aea3f370e52')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    LEFT JOIN geom_unprotected_areas g ON g.tileid = t.tileid
    WHERE t.nodegroupid = '7c8eb1f8-44e2-4239-afaa-9cbf1fadf160'::uuid
    GROUP BY t.parenttileid
),
geom_site_boundary AS (
    SELECT gg.tileid, ST_Collect(ST_Transform(gg.geom, 4326)) AS geom
    FROM public.geojson_geometries gg
    WHERE gg.nodeid = 'b18223c2-13ef-11f0-8695-0242ac170007'::uuid
    GROUP BY gg.tileid
),
site_boundary AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'site_boundary_description', arches_util.i18n_text(t.tiledata -> '63e48668-58f0-49fa-8767-abf412f54921'),
            'site_boundary', CASE WHEN g.geom IS NULL THEN NULL ELSE ST_AsGeoJSON(g.geom, 7)::jsonb END,
            'accuracy_remarks', arches_util.i18n_text(t.tiledata -> 'b182276e-13ef-11f0-8695-0242ac170007'),
            'latest_edit_type', arches_util.reference_flat(t.tiledata -> '6292f704-13f0-11f0-9284-0242ac170007'),
            'unprotected_areas', COALESCE(unprotected_areas.arr, '[]'::jsonb)
        ) AS obj
    FROM public.tiles t
    LEFT JOIN geom_site_boundary g ON g.tileid = t.tileid
    LEFT JOIN unprotected_areas unprotected_areas ON unprotected_areas.parenttileid = t.tileid
    WHERE t.nodegroupid = 'b18223c2-13ef-11f0-8695-0242ac170007'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS site_boundary FROM site_boundary;

CREATE UNIQUE INDEX mv_site_boundary_pk ON archaeological_site.mv_site_boundary (resourceinstanceid);
