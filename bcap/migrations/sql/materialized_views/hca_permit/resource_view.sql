-- GENERATED - edit per_spec.py and re-run generate.py. Do not hand-edit.
-- Wrapper view — the downstream contract. Repoint the backing matview here,
-- never rename this view. To ship v2: build mv_resource_v2, verify, repoint.

CREATE OR REPLACE VIEW hca_permit.resource AS SELECT * FROM hca_permit.mv_resource_v1;

COMMENT ON VIEW hca_permit.resource IS
'Stable read contract for the hca_permit graph. One row per resource instance. Backed by a '
'materialized view - repoint the backing matview here, never rename this. Arrays are always '
'[] when empty, never null. Cardinality-1 branches are null when the tile does not exist.';

-- GRANT SELECT ON hca_permit.resource TO <app_role>;   -- never grant on mv_resource_v1
