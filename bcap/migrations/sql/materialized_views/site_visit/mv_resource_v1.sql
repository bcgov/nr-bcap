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

DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_resource_v1 CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_resource_v1 AS
-- resource_instances is the row DRIVER, not a source of columns. It is what
-- guarantees one row per resource INCLUDING resources with zero tiles, and it
-- carries the only graphid filter in the stack. Drop the columns, keep the join.
SELECT
    r.resourceinstanceid,
    COALESCE(b0.ancestral_remains, '[]'::jsonb) AS ancestral_remains,
    b1.site_visit_details,
    COALESCE(b2.site_visit_location, '[]'::jsonb) AS site_visit_location,
    b3.related_documents,
    b4.remarks_and_recommendations,
    b5.identification,
    b6.archaeological_data,
    g_site_visit_location.site_visit_location_geom,
    g_site_visit_location.site_visit_location_geom_type,
    g_site_visit_location.site_visit_location_source_valid,
    g_site_visit_location.site_visit_location_points,
    g_site_visit_location.site_visit_location_lines,
    g_site_visit_location.site_visit_location_polygons,
    jsonb_build_object(
        'resourceinstanceid', r.resourceinstanceid,
        'ancestral_remains', COALESCE(b0.ancestral_remains, '[]'::jsonb),
        'site_visit_details', b1.site_visit_details,
        'site_visit_location', COALESCE(b2.site_visit_location, '[]'::jsonb),
        'related_documents', b3.related_documents,
        'remarks_and_recommendations', b4.remarks_and_recommendations,
        'identification', b5.identification,
        'archaeological_data', b6.archaeological_data
    ) AS resource
FROM public.resource_instances r
LEFT JOIN site_visit.mv_ancestral_remains b0 ON b0.resourceinstanceid = r.resourceinstanceid
LEFT JOIN site_visit.mv_site_visit_details b1 ON b1.resourceinstanceid = r.resourceinstanceid
LEFT JOIN site_visit.mv_site_visit_location b2 ON b2.resourceinstanceid = r.resourceinstanceid
LEFT JOIN site_visit.mv_related_documents b3 ON b3.resourceinstanceid = r.resourceinstanceid
LEFT JOIN site_visit.mv_remarks_and_recommendations b4 ON b4.resourceinstanceid = r.resourceinstanceid
LEFT JOIN site_visit.mv_identification b5 ON b5.resourceinstanceid = r.resourceinstanceid
LEFT JOIN site_visit.mv_archaeological_data b6 ON b6.resourceinstanceid = r.resourceinstanceid
LEFT JOIN site_visit.mv_geom_site_visit_location g_site_visit_location ON g_site_visit_location.resourceinstanceid = r.resourceinstanceid
WHERE r.graphid = '2da1c15f-1ab6-4122-9dbc-d10da693ac79'::uuid;

CREATE UNIQUE INDEX mv_resource_v1_pk  ON site_visit.mv_resource_v1 (resourceinstanceid);
CREATE INDEX mv_resource_v1_res        ON site_visit.mv_resource_v1 USING GIN (resource jsonb_path_ops);
CREATE INDEX mv_resource_v1_site_visit_location_gix      ON site_visit.mv_resource_v1 USING GIST (site_visit_location_geom);
CREATE INDEX mv_resource_v1_site_visit_location_poly_gix ON site_visit.mv_resource_v1 USING GIST (site_visit_location_polygons);
