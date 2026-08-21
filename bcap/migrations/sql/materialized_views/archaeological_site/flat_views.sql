-- GENERATED - edit as_spec.py and re-run generate.py. Do not hand-edit.

CREATE OR REPLACE VIEW archaeological_site.resource_flat AS SELECT * FROM archaeological_site.mv_resource_flat_v1;
CREATE OR REPLACE VIEW archaeological_site.heritage_site_location_flat AS SELECT * FROM archaeological_site.mv_heritage_site_location_flat_v1;
CREATE OR REPLACE VIEW archaeological_site.bc_property_address_flat AS SELECT * FROM archaeological_site.mv_bc_property_address_flat_v1;

COMMENT ON VIEW archaeological_site.resource_flat IS
'Flat archaeological_site records, one row per resource. Cardinality-n values are delimiter-joined text '
'(" | " between tiles, "; " within a tile) and are POSITIONALLY ALIGNED with their siblings - '
'empty slots are meaningful, do not strip them. Deeply nested subtrees live in the *_flat '
'companion tables, joined on resourceinstanceid.';
