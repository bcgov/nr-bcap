-- GENERATED - edit pub_spec.py and re-run generate.py. Do not hand-edit.
-- Wrapper view — the downstream contract. Repoint the backing matview here,
-- never rename this view. To ship v2: build mv_resource_v2, verify, repoint.

CREATE OR REPLACE VIEW publication.resource AS SELECT * FROM publication.mv_resource_v1;

COMMENT ON VIEW publication.resource IS
'Stable read contract for the publication graph. One row per resource instance. Backed by a '
'materialized view - repoint the backing matview here, never rename this. Arrays are always '
'[] when empty, never null. Cardinality-1 branches are null when the tile does not exist.';

-- GRANT SELECT ON publication.resource TO <app_role>;   -- never grant on mv_resource_v1
