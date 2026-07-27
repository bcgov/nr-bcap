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

DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_geom_site_visit_location CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_geom_site_visit_location AS
WITH per_tile AS (
    -- geojson_geometries.geom is SRID 3857 (Web Mercator). The Arches views
    -- ST_Transform on read; so do we. The ::geometry(...,4326) casts ENFORCE it -
    -- drop the transform and the build FAILS rather than publishing Mercator
    -- metres as though they were degrees.
    SELECT t.resourceinstanceid, t.tileid,
           ST_Collect(ST_Transform(g.geom, 4326)) AS geom
    FROM public.tiles t
    JOIN public.geojson_geometries g
      ON g.tileid = t.tileid AND g.nodeid = 'cf40edc0-13f0-11f0-9404-0242ac170007'::uuid
    WHERE t.nodegroupid = 'cf40edc0-13f0-11f0-9404-0242ac170007'::uuid
    GROUP BY t.resourceinstanceid, t.tileid
),
per_res AS (
    SELECT resourceinstanceid, ST_Collect(geom) AS raw
    FROM per_tile GROUP BY resourceinstanceid
),
fixed AS (
    -- ST_Collect over per-tile ST_Collect'd geometries yields a
    -- GEOMETRYCOLLECTION even when every part is a polygon. CollectionHomogenize
    -- collapses that to MULTIPOLYGON / MULTIPOINT / MULTILINESTRING, and leaves a
    -- GEOMETRYCOLLECTION only when the tiles GENUINELY mix types.
    -- MakeValid is applied TWICE on purpose: once on the raw collection, and again
    -- AFTER homogenize, because merging repaired parts into a single MULTIPOLYGON can
    -- itself produce an invalid geometry when tiles overlap. The outer MakeValid is
    -- what guarantees the published column is always valid.
    -- one bad polygon cannot break every downstream spatial query;
    -- site_visit_location_source_valid records which rows needed it. Fix those at source.
    SELECT resourceinstanceid, raw,
           ST_MakeValid(ST_CollectionHomogenize(ST_MakeValid(raw))) AS g
    FROM per_res
)
SELECT resourceinstanceid,
       g::geometry(Geometry, 4326)   AS site_visit_location_geom,
       ST_GeometryType(g)            AS site_visit_location_geom_type,
       ST_IsValid(raw)               AS site_visit_location_source_valid,
       -- CAST OUTSIDE THE CASE. Inside, the NULL branch is coerced to a bare
       -- `geometry` with no typmod, the CASE result drops to typmod -1, and the
       -- column becomes plain `geometry`. PostGIS then registers it in
       -- geometry_columns as srid=0 / type=GEOMETRY and QGIS/GeoServer cannot bind
       -- it. (A toy test with a CONSTANT input hides this - the planner folds the
       -- CASE away and the typmod survives. Against real tables it does not.)
       (CASE WHEN ST_IsEmpty(ST_CollectionExtract(g, 1)) THEN NULL
             ELSE ST_CollectionExtract(g, 1) END)::geometry(MultiPoint, 4326)      AS site_visit_location_points,
       (CASE WHEN ST_IsEmpty(ST_CollectionExtract(g, 2)) THEN NULL
             ELSE ST_CollectionExtract(g, 2) END)::geometry(MultiLineString, 4326) AS site_visit_location_lines,
       (CASE WHEN ST_IsEmpty(ST_CollectionExtract(g, 3)) THEN NULL
             ELSE ST_CollectionExtract(g, 3) END)::geometry(MultiPolygon, 4326)    AS site_visit_location_polygons
FROM fixed;

CREATE UNIQUE INDEX mv_geom_site_visit_location_pk   ON site_visit.mv_geom_site_visit_location (resourceinstanceid);
CREATE INDEX mv_geom_site_visit_location_gix         ON site_visit.mv_geom_site_visit_location USING GIST (site_visit_location_geom);
CREATE INDEX mv_geom_site_visit_location_poly_gix    ON site_visit.mv_geom_site_visit_location USING GIST (site_visit_location_polygons);
CREATE INDEX mv_geom_site_visit_location_pt_gix      ON site_visit.mv_geom_site_visit_location USING GIST (site_visit_location_points);
CREATE INDEX mv_geom_site_visit_location_line_gix    ON site_visit.mv_geom_site_visit_location USING GIST (site_visit_location_lines);
