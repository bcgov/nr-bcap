-- GENERATED - edit rep_spec.py and re-run generate.py. Do not hand-edit.
-- Graph 3e6a2880-14d4-11ec-9df0-5254008afee6
-- Requires 00_arches_util.sql (arches_util helpers) to be applied first.
--
-- Reads public.tiles DIRECTLY. The generated repository.* views are NOT used:
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

CREATE SCHEMA IF NOT EXISTS repository;

DROP MATERIALIZED VIEW IF EXISTS repository.mv_resource_v1 CASCADE;
CREATE MATERIALIZED VIEW repository.mv_resource_v1 AS
-- resource_instances is the row DRIVER, not a source of columns. It is what
-- guarantees one row per resource INCLUDING resources with zero tiles, and it
-- carries the only graphid filter in the stack. Drop the columns, keep the join.
SELECT
    r.resourceinstanceid,
    b0.contact_information,
    COALESCE(b1.repository_notes, '[]'::jsonb) AS repository_notes,
    b2.repository_identifier,
    g_physical_location.physical_location_geom,
    g_physical_location.physical_location_geom_type,
    g_physical_location.physical_location_source_valid,
    g_physical_location.physical_location_points,
    g_physical_location.physical_location_lines,
    g_physical_location.physical_location_polygons,
    jsonb_build_object(
        'resourceinstanceid', r.resourceinstanceid,
        'contact_information', b0.contact_information,
        'repository_notes', COALESCE(b1.repository_notes, '[]'::jsonb),
        'repository_identifier', b2.repository_identifier
    ) AS resource
FROM public.resource_instances r
LEFT JOIN repository.mv_contact_information b0 ON b0.resourceinstanceid = r.resourceinstanceid
LEFT JOIN repository.mv_repository_notes b1 ON b1.resourceinstanceid = r.resourceinstanceid
LEFT JOIN repository.mv_repository_identifier b2 ON b2.resourceinstanceid = r.resourceinstanceid
LEFT JOIN repository.mv_geom_physical_location g_physical_location ON g_physical_location.resourceinstanceid = r.resourceinstanceid
WHERE r.graphid = '3e6a2880-14d4-11ec-9df0-5254008afee6'::uuid;

CREATE UNIQUE INDEX mv_resource_v1_pk  ON repository.mv_resource_v1 (resourceinstanceid);
CREATE INDEX mv_resource_v1_res        ON repository.mv_resource_v1 USING GIN (resource jsonb_path_ops);
CREATE INDEX mv_resource_v1_physical_location_gix      ON repository.mv_resource_v1 USING GIST (physical_location_geom);
CREATE INDEX mv_resource_v1_physical_location_poly_gix ON repository.mv_resource_v1 USING GIST (physical_location_polygons);
