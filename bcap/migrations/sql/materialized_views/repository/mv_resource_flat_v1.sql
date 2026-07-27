-- GENERATED - edit rep_spec.py and re-run generate.py.
-- Requires repository/mv_resource_v1.sql to be applied first.
--
-- Built ON TOP OF mv_resource_v1: one source of truth, zero joins.
-- CONTRACT:
--   * cardinality-1 fields keep REAL TYPES (date, numeric, boolean, text)
--   * cardinality-n fields are TEXT CSV: ' | ' between tiles, '; ' within a tile
--   * POSITIONAL ALIGNMENT IS THE CONTRACT. Null elements emit an EMPTY SLOT.
--   * references come in pairs: x (labels) + x_ids

SET client_min_messages = warning;

DROP MATERIALIZED VIEW IF EXISTS repository.mv_resource_flat_v1 CASCADE;
CREATE MATERIALIZED VIEW repository.mv_resource_flat_v1 AS
SELECT
    r.resourceinstanceid,
    r.physical_location_geom,
    r.physical_location_geom_type,
    r.physical_location_source_valid,
    r.physical_location_points,
    r.physical_location_lines,
    r.physical_location_polygons,
    r.contact_information ->> 'city' AS city,
    arches_util.a2csv(r.contact_information -> 'province', 'label', ' | ') AS province,
    arches_util.a2csv(r.contact_information -> 'province', 'list_item_id', ' | ') AS province_ids,
    r.contact_information ->> 'address_line_1' AS address_line_1,
    r.contact_information ->> 'address_line_2' AS address_line_2,
    r.contact_information ->> 'postal_code' AS postal_code,
    r.contact_information ->> 'address_notes' AS address_notes,
    r.contact_information ->> 'primary_email' AS primary_email,
    r.contact_information ->> 'place_description' AS place_description,
    arches_util.deep_csv(r.repository_notes, '{}'::text[], 'note', ' | ') AS note,
    jsonb_array_length(arches_util.as_array(r.repository_notes)) AS repository_notes_count,
    r.repository_identifier ->> 'repository_name' AS repository_name,
    r.repository_identifier ->> 'repository_location_code' AS repository_location_code,
    arches_util.deep_csv(r.repository_identifier -> 'alternate_identifiers', '{}'::text[], 'alternate_name', ' | ') AS alternate_name,
    arches_util.deep_csv(r.repository_identifier -> 'alternate_identifiers', '{}'::text[], 'alternate_code', ' | ') AS alternate_code,
    jsonb_array_length(arches_util.as_array(r.repository_identifier -> 'alternate_identifiers')) AS alternate_identifiers_count
FROM repository.mv_resource_v1 r;

CREATE UNIQUE INDEX mv_resource_flat_v1_pk ON repository.mv_resource_flat_v1 (resourceinstanceid);
CREATE INDEX mv_resource_flat_v1_physical_location_gix ON repository.mv_resource_flat_v1 USING GIST (physical_location_geom);
