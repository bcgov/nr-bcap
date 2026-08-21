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

DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_resource_v1 CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_resource_v1 AS
-- resource_instances is the row DRIVER, not a source of columns. It is what
-- guarantees one row per resource INCLUDING resources with zero tiles, and it
-- carries the only graphid filter in the stack. Drop the columns, keep the join.
SELECT
    r.resourceinstanceid,
    b0.site_boundary,
    COALESCE(b1.site_record_admin, '[]'::jsonb) AS site_record_admin,
    COALESCE(b2.external_url, '[]'::jsonb) AS external_url,
    b3.ancestral_remains,
    b4.archaeological_data,
    b5.identification_and_registration,
    b6.remarks_and_restricted_information,
    COALESCE(b7.heritage_site_location, '[]'::jsonb) AS heritage_site_location,
    b8.related_documents,
    g_site_boundary.site_boundary_geom,
    g_site_boundary.site_boundary_geom_type,
    g_site_boundary.site_boundary_source_valid,
    g_site_boundary.site_boundary_points,
    g_site_boundary.site_boundary_lines,
    g_site_boundary.site_boundary_polygons,
    g_unprotected_areas.unprotected_areas_geom,
    g_unprotected_areas.unprotected_areas_geom_type,
    g_unprotected_areas.unprotected_areas_source_valid,
    g_unprotected_areas.unprotected_areas_points,
    g_unprotected_areas.unprotected_areas_lines,
    g_unprotected_areas.unprotected_areas_polygons,
    jsonb_build_object(
        'resourceinstanceid', r.resourceinstanceid,
        'site_boundary', b0.site_boundary,
        'site_record_admin', COALESCE(b1.site_record_admin, '[]'::jsonb),
        'external_url', COALESCE(b2.external_url, '[]'::jsonb),
        'ancestral_remains', b3.ancestral_remains,
        'archaeological_data', b4.archaeological_data,
        'identification_and_registration', b5.identification_and_registration,
        'remarks_and_restricted_information', b6.remarks_and_restricted_information,
        'heritage_site_location', COALESCE(b7.heritage_site_location, '[]'::jsonb),
        'related_documents', b8.related_documents
    ) AS resource
FROM public.resource_instances r
LEFT JOIN archaeological_site.mv_site_boundary b0 ON b0.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_site_record_admin b1 ON b1.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_external_url b2 ON b2.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_ancestral_remains b3 ON b3.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_archaeological_data b4 ON b4.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_identification_and_registration b5 ON b5.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_remarks_and_restricted_information b6 ON b6.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_heritage_site_location b7 ON b7.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_related_documents b8 ON b8.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_geom_site_boundary g_site_boundary ON g_site_boundary.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_geom_unprotected_areas g_unprotected_areas ON g_unprotected_areas.resourceinstanceid = r.resourceinstanceid
WHERE r.graphid = 'cef9c510-e3e6-4057-ac08-89ad926180b4'::uuid;

CREATE UNIQUE INDEX mv_resource_v1_pk  ON archaeological_site.mv_resource_v1 (resourceinstanceid);
CREATE INDEX mv_resource_v1_res        ON archaeological_site.mv_resource_v1 USING GIN (resource jsonb_path_ops);
CREATE INDEX mv_resource_v1_site_boundary_gix      ON archaeological_site.mv_resource_v1 USING GIST (site_boundary_geom);
CREATE INDEX mv_resource_v1_site_boundary_poly_gix ON archaeological_site.mv_resource_v1 USING GIST (site_boundary_polygons);
CREATE INDEX mv_resource_v1_unprotected_areas_gix      ON archaeological_site.mv_resource_v1 USING GIST (unprotected_areas_geom);
CREATE INDEX mv_resource_v1_unprotected_areas_poly_gix ON archaeological_site.mv_resource_v1 USING GIST (unprotected_areas_polygons);
