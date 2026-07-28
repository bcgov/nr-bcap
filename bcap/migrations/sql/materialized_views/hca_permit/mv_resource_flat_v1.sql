-- GENERATED - edit per_spec.py and re-run generate.py.
-- Requires hca_permit/mv_resource_v1.sql to be applied first.
--
-- Built ON TOP OF mv_resource_v1: one source of truth, zero joins.
-- CONTRACT:
--   * cardinality-1 fields keep REAL TYPES (date, numeric, boolean, text)
--   * cardinality-n fields are TEXT CSV: ' | ' between tiles, '; ' within a tile
--   * POSITIONAL ALIGNMENT IS THE CONTRACT. Null elements emit an EMPTY SLOT.
--   * references come in pairs: x (labels) + x_ids

SET client_min_messages = warning;

DROP MATERIALIZED VIEW IF EXISTS hca_permit.mv_resource_flat_v1 CASCADE;
CREATE MATERIALIZED VIEW hca_permit.mv_resource_flat_v1 AS
SELECT
    r.resourceinstanceid,
    r.permit_identification ->> 'permit_number' AS permit_number,
    arches_util.a2csv(r.permit_identification -> 'issuing_agency', 'label', ' | ') AS issuing_agency,
    arches_util.a2csv(r.permit_identification -> 'issuing_agency', 'list_item_id', ' | ') AS issuing_agency_ids,
    arches_util.a2csv(r.permit_identification -> 'hca_permit_type', 'label', ' | ') AS hca_permit_type,
    arches_util.a2csv(r.permit_identification -> 'hca_permit_type', 'list_item_id', ' | ') AS hca_permit_type_ids,
    arches_util.resource_names_csv(r.permit_identification -> 'permit_holder', ' | ') AS permit_holder,
    arches_util.a2csv(r.permit_identification -> 'permit_holder', NULL, ' | ') AS permit_holder_ids
FROM hca_permit.mv_resource_v1 r;

CREATE UNIQUE INDEX mv_resource_flat_v1_pk ON hca_permit.mv_resource_flat_v1 (resourceinstanceid);
