-- GENERATED - edit sv_spec.py and re-run generate.py. Do not hand-edit.
-- Wrapper view — the downstream contract. Repoint the backing matview here,
-- never rename this view. To ship v2: build mv_resource_v2, verify, repoint.

CREATE OR REPLACE VIEW site_visit.resource AS SELECT * FROM site_visit.mv_resource_v1;

COMMENT ON VIEW site_visit.resource IS
'Stable read contract for the site_visit graph. One row per resource instance. Backed by a '
'materialized view - repoint the backing matview here, never rename this. Arrays are always '
'[] when empty, never null. Cardinality-1 branches are null when the tile does not exist.';

-- GRANT SELECT ON site_visit.resource TO <app_role>;   -- never grant on mv_resource_v1
