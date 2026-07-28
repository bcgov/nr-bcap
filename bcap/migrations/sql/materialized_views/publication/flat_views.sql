-- GENERATED - edit pub_spec.py and re-run generate.py. Do not hand-edit.

CREATE OR REPLACE VIEW publication.resource_flat AS SELECT * FROM publication.mv_resource_flat_v1;

COMMENT ON VIEW publication.resource_flat IS
'Flat publication records, one row per resource. Cardinality-n values are delimiter-joined text '
'(" | " between tiles, "; " within a tile) and are POSITIONALLY ALIGNED with their siblings - '
'empty slots are meaningful, do not strip them. Deeply nested subtrees live in the *_flat '
'companion tables, joined on resourceinstanceid.';
