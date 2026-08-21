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
-- site_visit_location  (cardinality n)  children: biogeography
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_site_visit_location CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_site_visit_location AS
WITH biogeography AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'biogeography_description', arches_util.i18n_text(t.tiledata -> '95e5f9b6-71cd-4769-b365-9155442954ec'),
            'biogeography_type', arches_util.reference_flat(t.tiledata -> '5270c773-125c-4223-868e-badeb5cf5f78'),
            'biogeography_name', arches_util.i18n_text(t.tiledata -> '5c7d9c33-c53e-45ea-b503-d4bbeaa9e31c')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '6abfca2d-8f5d-458a-b128-ab8ba49c1921'::uuid
    GROUP BY t.parenttileid
),
geom_site_visit_location AS (
    SELECT gg.tileid, ST_Collect(ST_Transform(gg.geom, 4326)) AS geom
    FROM public.geojson_geometries gg
    WHERE gg.nodeid = 'cf40edc0-13f0-11f0-9404-0242ac170007'::uuid
    GROUP BY gg.tileid
),
site_visit_location AS (
    SELECT t.resourceinstanceid AS resourceinstanceid,
           jsonb_agg(jsonb_build_object(
            'site_visit_location', CASE WHEN g.geom IS NULL THEN NULL ELSE ST_AsGeoJSON(g.geom, 7)::jsonb END,
            'latest_edit_type', arches_util.reference_flat(t.tiledata -> 'cf40f158-13f0-11f0-9404-0242ac170007'),
            'boundary_type', arches_util.reference_flat(t.tiledata -> '9aea2913-e4ee-43dd-904c-abee908f61b6'),
            'location_and_access', arches_util.i18n_text(t.tiledata -> 'cca03a72-13fe-11f0-99e9-0242ac170007'),
            'accuracy_remarks', arches_util.i18n_text(t.tiledata -> 'cf40f40a-13f0-11f0-9404-0242ac170007'),
            'biogeography', COALESCE(biogeography.arr, '[]'::jsonb)
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    LEFT JOIN geom_site_visit_location g ON g.tileid = t.tileid
    LEFT JOIN biogeography biogeography ON biogeography.parenttileid = t.tileid
    WHERE t.nodegroupid = 'cf40edc0-13f0-11f0-9404-0242ac170007'::uuid
    GROUP BY t.resourceinstanceid
)
SELECT resourceinstanceid, arr AS site_visit_location FROM site_visit_location;

CREATE UNIQUE INDEX mv_site_visit_location_pk ON site_visit.mv_site_visit_location (resourceinstanceid);
