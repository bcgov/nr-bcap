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

DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_site_location_flat_v1 CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_site_location_flat_v1 AS
SELECT
    r.resourceinstanceid,
    g.ord AS site_location_index,
    arches_util.deep_csv_nested(g.t -> 'biogeography', '{}'::text[], 'biogeography_type', 'label', ' | ', '; ') AS biogeography_type,
    arches_util.deep_csv_nested(g.t -> 'biogeography', '{}'::text[], 'biogeography_type', 'list_item_id', ' | ', '; ') AS biogeography_type_ids,
    arches_util.deep_csv(g.t -> 'biogeography', '{}'::text[], 'biogeography_name', ' | ') AS biogeography_name,
    arches_util.deep_csv(g.t -> 'biogeography', '{}'::text[], 'biogeography_description', ' | ') AS biogeography_description,
    jsonb_array_length(arches_util.as_array(g.t -> 'biogeography')) AS biogeography_count,
    (g.t -> 'elevation' ->> 'gis_lower_elevation')::numeric AS gis_lower_elevation,
    (g.t -> 'elevation' ->> 'gis_upper_elevation')::numeric AS gis_upper_elevation,
    g.t -> 'site_tenure' -> 'site_tenure_remarks' ->> 'site_tenure_remarks' AS site_tenure_remarks,
    g.t -> 'site_tenure' -> 'site_tenure_type' ->> 'site_tenure_type' AS site_tenure_type,
    g.t -> 'site_tenure' -> 'site_tenure_type' ->> 'site_tenure_identifier' AS site_tenure_identifier,
    arches_util.deep_csv(g.t -> 'elevation' -> 'elevation_comments', '{}'::text[], 'elevation_comments', ' | ') AS elevation_comments,
    jsonb_array_length(arches_util.as_array(g.t -> 'elevation' -> 'elevation_comments')) AS elevation_comments_count
FROM archaeological_site.mv_resource_v1 r,
     LATERAL jsonb_array_elements(arches_util.as_array(r.site_location))
             WITH ORDINALITY AS g(t, ord);

CREATE UNIQUE INDEX mv_site_location_flat_v1_pk ON archaeological_site.mv_site_location_flat_v1 (resourceinstanceid, site_location_index);
