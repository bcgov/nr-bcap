-- GENERATED - edit sv_spec.py and re-run generate.py.
-- Requires site_visit/mv_resource_v1.sql to be applied first.
--
-- Built ON TOP OF mv_resource_v1: one source of truth, zero joins.
-- CONTRACT:
--   * cardinality-1 fields keep REAL TYPES (date, numeric, boolean, text)
--   * cardinality-n fields are TEXT CSV: ' | ' between tiles, '; ' within a tile
--   * POSITIONAL ALIGNMENT IS THE CONTRACT. Null elements emit an EMPTY SLOT.
--   * references come in pairs: x (labels) + x_ids

SET client_min_messages = warning;

DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_site_visit_location_flat_v1 CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_site_visit_location_flat_v1 AS
SELECT
    r.resourceinstanceid,
    g.ord AS site_visit_location_index,
    arches_util.a2csv(g.t -> 'latest_edit_type', 'label', ' | ') AS latest_edit_type,
    arches_util.a2csv(g.t -> 'latest_edit_type', 'list_item_id', ' | ') AS latest_edit_type_ids,
    arches_util.a2csv(g.t -> 'boundary_type', 'label', ' | ') AS boundary_type,
    arches_util.a2csv(g.t -> 'boundary_type', 'list_item_id', ' | ') AS boundary_type_ids,
    g.t ->> 'location_and_access' AS location_and_access,
    g.t ->> 'accuracy_remarks' AS accuracy_remarks,
    arches_util.deep_csv(g.t -> 'biogeography', '{}'::text[], 'biogeography_description', ' | ') AS biogeography_description,
    arches_util.deep_csv_nested(g.t -> 'biogeography', '{}'::text[], 'biogeography_type', 'label', ' | ', '; ') AS biogeography_type,
    arches_util.deep_csv_nested(g.t -> 'biogeography', '{}'::text[], 'biogeography_type', 'list_item_id', ' | ', '; ') AS biogeography_type_ids,
    arches_util.deep_csv(g.t -> 'biogeography', '{}'::text[], 'biogeography_name', ' | ') AS biogeography_name,
    jsonb_array_length(arches_util.as_array(g.t -> 'biogeography')) AS biogeography_count
FROM site_visit.mv_resource_v1 r,
     LATERAL jsonb_array_elements(arches_util.as_array(r.site_visit_location))
             WITH ORDINALITY AS g(t, ord);

CREATE UNIQUE INDEX mv_site_visit_location_flat_v1_pk ON site_visit.mv_site_visit_location_flat_v1 (resourceinstanceid, site_visit_location_index);
