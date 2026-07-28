-- GENERATED - edit per_spec.py and re-run generate.py. Do not hand-edit.
-- Graph f4b391f1-79d1-4886-ab2d-d72a197a9f21
-- Requires 00_arches_util.sql (arches_util helpers) to be applied first.
--
-- Reads public.tiles DIRECTLY. The generated hca_permit.* views are NOT used:
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

CREATE SCHEMA IF NOT EXISTS hca_permit;

DROP MATERIALIZED VIEW IF EXISTS hca_permit.mv_resource_v1 CASCADE;
CREATE MATERIALIZED VIEW hca_permit.mv_resource_v1 AS
-- resource_instances is the row DRIVER, not a source of columns. It is what
-- guarantees one row per resource INCLUDING resources with zero tiles, and it
-- carries the only graphid filter in the stack. Drop the columns, keep the join.
SELECT
    r.resourceinstanceid,
    b0.permit_identification,
    jsonb_build_object(
        'resourceinstanceid', r.resourceinstanceid,
        'permit_identification', b0.permit_identification
    ) AS resource
FROM public.resource_instances r
LEFT JOIN hca_permit.mv_permit_identification b0 ON b0.resourceinstanceid = r.resourceinstanceid
WHERE r.graphid = 'f4b391f1-79d1-4886-ab2d-d72a197a9f21'::uuid;

CREATE UNIQUE INDEX mv_resource_v1_pk  ON hca_permit.mv_resource_v1 (resourceinstanceid);
CREATE INDEX mv_resource_v1_res        ON hca_permit.mv_resource_v1 USING GIN (resource jsonb_path_ops);
