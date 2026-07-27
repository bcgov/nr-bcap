-- GENERATED - edit per_spec.py and re-run generate.py. Do not hand-edit.

CREATE OR REPLACE VIEW hca_permit.resource_flat AS SELECT * FROM hca_permit.mv_resource_flat_v1;

COMMENT ON VIEW hca_permit.resource_flat IS
'Flat hca_permit records, one row per resource. Cardinality-n values are delimiter-joined text '
'(" | " between tiles, "; " within a tile) and are POSITIONALLY ALIGNED with their siblings - '
'empty slots are meaningful, do not strip them. Deeply nested subtrees live in the *_flat '
'companion tables, joined on resourceinstanceid.';
