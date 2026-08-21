-- GENERATED - edit as_spec.py and re-run generate.py.
-- Requires archaeological_site/mv_resource_v1.sql to be applied first.
--
-- Built ON TOP OF mv_resource_v1: one source of truth, zero joins.
-- CONTRACT:
--   * cardinality-1 fields keep REAL TYPES (date, numeric, boolean, text)
--   * cardinality-n fields are TEXT CSV: ' | ' between tiles, '; ' within a tile
--   * POSITIONAL ALIGNMENT IS THE CONTRACT. Null elements emit an EMPTY SLOT.
--   * references come in pairs: x (labels) + x_ids

SET client_min_messages = warning;

DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_bc_property_address_flat_v1 CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_bc_property_address_flat_v1 AS
SELECT
    r.resourceinstanceid,
    p.ord AS heritage_site_location_index,
    g.ord AS bc_property_address_index,
    g.t ->> 'street_name' AS street_name,
    g.t ->> 'street_number' AS street_number,
    g.t ->> 'address_remarks' AS address_remarks,
    g.t ->> 'city' AS city,
    g.t ->> 'postal_code' AS postal_code,
    arches_util.deep_csv(g.t -> 'bc_property_legal_description', '{}'::text[], 'pid', ' | ') AS pid,
    arches_util.deep_csv(g.t -> 'bc_property_legal_description', '{}'::text[], 'pin', ' | ') AS pin,
    arches_util.deep_csv(g.t -> 'bc_property_legal_description', '{}'::text[], 'legal_description', ' | ') AS legal_description,
    arches_util.deep_csv(g.t -> 'bc_property_legal_description', '{}'::text[], 'legal_address_remarks', ' | ') AS legal_address_remarks,
    jsonb_array_length(arches_util.as_array(g.t -> 'bc_property_legal_description')) AS bc_property_legal_description_count
FROM archaeological_site.mv_resource_v1 r,
     LATERAL jsonb_array_elements(arches_util.as_array(r.heritage_site_location))
             WITH ORDINALITY AS p(t, ord),
     LATERAL jsonb_array_elements(arches_util.as_array(p.t -> 'bc_property_address'))
             WITH ORDINALITY AS g(t, ord);

CREATE UNIQUE INDEX mv_bc_property_address_flat_v1_pk ON archaeological_site.mv_bc_property_address_flat_v1 (resourceinstanceid, heritage_site_location_index, bc_property_address_index);
