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

-- ---------------------------------------------------------------------
-- permit_identification  (cardinality 1)
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS hca_permit.mv_permit_identification CASCADE;
CREATE MATERIALIZED VIEW hca_permit.mv_permit_identification AS
WITH permit_identification AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'permit_number', t.tiledata ->> '673aa382-df62-11ef-9ad0-0242ac170009',
            'issuing_agency', arches_util.reference_flat(t.tiledata -> '7f0349ce-df62-11ef-9ad0-0242ac170009'),
            'hca_permit_type', arches_util.reference_flat(t.tiledata -> '9c8ad2f0-df62-11ef-9ad0-0242ac170009'),
            'permit_holder', arches_util.resource_ids(t.tiledata -> '3af6f67a-5926-11f0-bef3-0242ac170006')
        ) AS obj
    FROM public.tiles t
    WHERE t.nodegroupid = '588c9c3c-df62-11ef-9ad0-0242ac170009'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS permit_identification FROM permit_identification;

CREATE UNIQUE INDEX mv_permit_identification_pk ON hca_permit.mv_permit_identification (resourceinstanceid);
