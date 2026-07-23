-- =====================================================================
--  site_visit :: FLAT DENORMALIZED TABLE
--  site_visit.mv_resource_flat_v1  +  site_visit.resource_flat (wrapper)
--
--  Built ON TOP OF site_visit.mv_resource_v1. That is deliberate:
--    * one source of truth - the node-UUID mapping exists in exactly one place,
--      so the flat table cannot drift from the nested one
--    * zero joins - a single seq scan of an already-materialized, one-row-per-
--      resource table. The jsonb round-trip costs something, but it is cheap
--      next to re-deriving 24 nodegroups from tiles a second time.
--
--  Refresh AFTER mv_resource_v1. See site_visit.refresh_resource_flat() below.
--
--  =====================================================================
--  READ THIS BEFORE ANYONE BUILDS A REPORT ON IT
--  =====================================================================
--
--  1. POSITIONAL ALIGNMENT IS THE WHOLE CONTRACT.
--     Sibling columns from the same cardinality-n nodegroup are aligned by
--     position. If cultural_material_type is "Lithic | Faunal | Ceramic" then
--     number_of_artifacts has THREE slots too - "12 |  | 40" means Faunal had
--     no count, not that Ceramic had 40 and Faunal is missing.
--
--     This only holds because NULL elements emit an EMPTY SLOT rather than being
--     skipped. Every helper below does that. Do not "clean up" the empty slots.
--
--     WHERE IT DOES NOT HOLD: nested reference / file columns. A tile with two
--     member_roles contributes "Recorder; Supervisor" to that one slot, so the
--     tile-to-slot mapping survives, but an item-level position does not. And
--     biogeography_* is three levels deep (loc tile -> biogeo tile -> ref item);
--     those four columns align WITH EACH OTHER but NOT with the loc-tile columns
--     beside them. Flagged again in COMMENT ON COLUMN.
--
--  2. DELIMITERS.
--        ' | '  between tiles   (rows of a cardinality-n nodegroup)
--        '; '   within one tile (multi-select reference, file list)
--     Literal '|' in source text is replaced with '/' so the delimiter cannot
--     collide. Your free-text fields (remarks, descriptions, location_and_access)
--     WILL contain commas, which is why the delimiter is not a comma. Do not
--     switch it to one.
--
--  3. TYPES.
--     Cardinality-1 fields keep REAL TYPES (date, boolean, text).
--     Cardinality-n fields are TEXT, because concatenation forces text. A column
--     holding "12 | 40" cannot be numeric, and keeping only the first value to
--     preserve the type would be worse than admitting it is a list. If you need
--     numeric aggregation over these, do it against mv_resource_v1's jsonb, not
--     here - this table is for reporting and export, not analysis.
--
--  4. THIS IS LOSSY AND ONE-WAY. You cannot reconstruct the resource from it.
--     mv_resource_v1 remains the round-trippable object. Do not let anything
--     write back from here.
-- =====================================================================


-- ---------------------------------------------------------------------
-- Helpers.  All three preserve empty slots. That is the point.
-- ---------------------------------------------------------------------

-- Flatten a jsonb ARRAY into a delimited string.
--   field IS NULL -> elements are scalars (e.g. a list of uuid strings)
--   field given   -> elements are objects; pluck that key
-- NULL elements become '' so sibling columns stay positionally aligned.
-- An empty or absent array returns NULL (not ''), so "no tiles" is
-- distinguishable from "one tile with an empty value".
CREATE OR REPLACE FUNCTION arches_util.a2csv(
    val jsonb, field text DEFAULT NULL, delim text DEFAULT ' | ')
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN jsonb_typeof(val) <> 'array' THEN NULL
        WHEN jsonb_array_length(val) = 0  THEN NULL
        ELSE (
            SELECT string_agg(
                replace(COALESCE(
                    CASE WHEN field IS NULL THEN e.item #>> '{}'
                         ELSE e.item ->> field END, ''), '|', '/'),
                delim ORDER BY e.ord)
            FROM jsonb_array_elements(val) WITH ORDINALITY AS e(item, ord))
    END;
$$;

-- Two-level flatten: for each element of `arr`, take element->key (itself an
-- array), collapse it with inner_delim, then join those with delim.
-- A tile whose inner array is empty still contributes an EMPTY SLOT.
CREATE OR REPLACE FUNCTION arches_util.a2csv_nested(
    arr jsonb, key text, field text DEFAULT NULL,
    delim text DEFAULT ' | ', inner_delim text DEFAULT '; ')
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN jsonb_typeof(arr) <> 'array' THEN NULL
        WHEN jsonb_array_length(arr) = 0  THEN NULL
        ELSE (
            SELECT string_agg(
                COALESCE(arches_util.a2csv(e.item -> key, field, inner_delim), ''),
                delim ORDER BY e.ord)
            FROM jsonb_array_elements(arr) WITH ORDINALITY AS e(item, ord))
    END;
$$;

-- Arbitrary-depth flatten via jsonpath. Used ONLY for biogeography_*, which sits
-- three levels down. NOTE: this collapses across ALL parent tiles, so its output
-- does NOT align positionally with columns derived from the parent tile array.
-- Document order is preserved, so path_csv columns align with EACH OTHER.
CREATE OR REPLACE FUNCTION arches_util.path_csv(
    val jsonb, path jsonpath, delim text DEFAULT ' | ')
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT NULLIF(string_agg(
        replace(COALESCE(x.v #>> '{}', ''), '|', '/'), delim ORDER BY x.ord), '')
    FROM jsonb_path_query(COALESCE(val, '[]'::jsonb), path)
         WITH ORDINALITY AS x(v, ord);
$$;


-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_resource_flat_v1 CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_resource_flat_v1 AS
SELECT
    r.resourceinstanceid,
    r.site_visit_geom,
    ST_Y(ST_Centroid(r.site_visit_geom))::numeric(10,7) AS centroid_lat,
    ST_X(ST_Centroid(r.site_visit_geom))::numeric(10,7) AS centroid_lon,
    arches_util.a2csv(r.site_visit_details -> 'site_visit_type', 'label', ' | ') AS site_visit_type,
    arches_util.a2csv(r.site_visit_details -> 'site_visit_type', 'list_item_id', ' | ') AS site_visit_type_ids,
    (r.site_visit_details ->> 'is_site_visit_permitted')::boolean AS is_site_visit_permitted,
    (r.site_visit_details ->> 'first_date_of_site_visit')::date AS first_date_of_site_visit,
    (r.site_visit_details ->> 'last_date_of_site_visit')::date AS last_date_of_site_visit,
    r.site_visit_details ->> 'project_description' AS project_description,
    arches_util.resource_name(arches_util.to_uuid(r.site_visit_details ->> 'affiliation')) AS affiliation,
    r.site_visit_details ->> 'affiliation' AS affiliation_id,
    arches_util.resource_name(arches_util.to_uuid(r.site_visit_details ->> 'archaeological_site')) AS archaeological_site,
    r.site_visit_details ->> 'archaeological_site' AS archaeological_site_id,
    arches_util.resource_names_csv(r.site_visit_details -> 'associated_permit', ' | ') AS associated_permit,
    arches_util.a2csv(r.site_visit_details -> 'associated_permit', NULL, ' | ') AS associated_permit_ids,
    arches_util.resource_names_csv(r.site_visit_details -> 'site_form_authors', ' | ') AS site_form_authors,
    arches_util.a2csv(r.site_visit_details -> 'site_form_authors', NULL, ' | ') AS site_form_authors_ids,
    arches_util.resource_name_col(r.site_visit_details -> 'site_visit_team' -> 'team_member', 'team_member', ' | ') AS team_member,
    arches_util.a2csv(r.site_visit_details -> 'site_visit_team' -> 'team_member', 'team_member', ' | ') AS team_member_ids,
    arches_util.a2csv_nested(r.site_visit_details -> 'site_visit_team' -> 'team_member', 'member_roles', 'label', ' | ', '; ') AS member_roles,
    arches_util.a2csv_nested(r.site_visit_details -> 'site_visit_team' -> 'team_member', 'member_roles', 'list_item_id', ' | ', '; ') AS member_roles_ids,
    arches_util.a2csv(r.site_visit_details -> 'site_visit_team' -> 'team_member', 'was_on_site', ' | ') AS was_on_site,
    jsonb_array_length(arches_util.as_array(r.site_visit_details -> 'site_visit_team' -> 'team_member')) AS team_member_count,
    arches_util.a2csv(r.identification -> 'new_site_names', 'name', ' | ') AS site_name,   -- node is `name`; renamed - `name` is too generic for a flat table
    arches_util.a2csv_nested(r.identification -> 'new_site_names', 'name_type', 'label', ' | ', '; ') AS name_type,
    arches_util.a2csv_nested(r.identification -> 'new_site_names', 'name_type', 'list_item_id', ' | ', '; ') AS name_type_ids,
    arches_util.a2csv(r.identification -> 'new_site_names', 'name_remarks', ' | ') AS name_remarks,
    arches_util.resource_name_col(r.identification -> 'new_site_names', 'assigned_or_reported_by', ' | ') AS assigned_or_reported_by,
    arches_util.a2csv(r.identification -> 'new_site_names', 'assigned_or_reported_by', ' | ') AS assigned_or_reported_by_ids,
    arches_util.a2csv(r.identification -> 'new_site_names', 'assigned_or_reported_date', ' | ') AS assigned_or_reported_date,
    jsonb_array_length(arches_util.as_array(r.identification -> 'new_site_names')) AS new_site_names_count,
    r.identification -> 'temporary_number' ->> 'temporary_number' AS temporary_number,
    arches_util.resource_name(arches_util.to_uuid(r.identification -> 'temporary_number' ->> 'temporary_number_assigned_by')) AS temporary_number_assigned_by,
    r.identification -> 'temporary_number' ->> 'temporary_number_assigned_by' AS temporary_number_assigned_by_id,
    (r.identification -> 'temporary_number' ->> 'temporary_number_assigned_date')::date AS temporary_number_assigned_date,
    arches_util.a2csv_nested(r.archaeological_data -> 'cultural_material', 'cultural_material_type', 'label', ' | ', '; ') AS cultural_material_type,
    arches_util.a2csv_nested(r.archaeological_data -> 'cultural_material', 'cultural_material_type', 'list_item_id', ' | ', '; ') AS cultural_material_type_ids,
    arches_util.a2csv_nested(r.archaeological_data -> 'cultural_material', 'cultural_material_status', 'label', ' | ', '; ') AS cultural_material_status,
    arches_util.a2csv_nested(r.archaeological_data -> 'cultural_material', 'cultural_material_status', 'list_item_id', ' | ', '; ') AS cultural_material_status_ids,
    arches_util.a2csv(r.archaeological_data -> 'cultural_material', 'cultural_material_details', ' | ') AS cultural_material_details,
    arches_util.a2csv(r.archaeological_data -> 'cultural_material', 'number_of_artifacts', ' | ') AS number_of_artifacts,
    arches_util.resource_name_col(r.archaeological_data -> 'cultural_material', 'repository', ' | ') AS repository,
    arches_util.a2csv(r.archaeological_data -> 'cultural_material', 'repository', ' | ') AS repository_ids,
    jsonb_array_length(arches_util.as_array(r.archaeological_data -> 'cultural_material')) AS cultural_material_count,
    arches_util.a2csv(r.archaeological_data -> 'stratigraphy', 'stratigraphy', ' | ') AS stratigraphy,
    jsonb_array_length(arches_util.as_array(r.archaeological_data -> 'stratigraphy')) AS stratigraphy_count,
    arches_util.a2csv_nested(r.archaeological_data -> 'archaeological_feature', 'archaeological_feature', 'label', ' | ', '; ') AS archaeological_feature,
    arches_util.a2csv_nested(r.archaeological_data -> 'archaeological_feature', 'archaeological_feature', 'list_item_id', ' | ', '; ') AS archaeological_feature_ids,
    arches_util.a2csv(r.archaeological_data -> 'archaeological_feature', 'feature_count', ' | ') AS feature_count,
    arches_util.a2csv(r.archaeological_data -> 'archaeological_feature', 'feature_remarks', ' | ') AS feature_remarks,
    jsonb_array_length(arches_util.as_array(r.archaeological_data -> 'archaeological_feature')) AS archaeological_feature_count,
    arches_util.a2csv(r.archaeological_data -> 'chronology', 'start_year', ' | ') AS start_year,
    arches_util.a2csv_nested(r.archaeological_data -> 'chronology', 'start_year_qualifier', 'label', ' | ', '; ') AS start_year_qualifier,
    arches_util.a2csv_nested(r.archaeological_data -> 'chronology', 'start_year_qualifier', 'list_item_id', ' | ', '; ') AS start_year_qualifier_ids,
    arches_util.a2csv_nested(r.archaeological_data -> 'chronology', 'start_year_calendar', 'label', ' | ', '; ') AS start_year_calendar,
    arches_util.a2csv_nested(r.archaeological_data -> 'chronology', 'start_year_calendar', 'list_item_id', ' | ', '; ') AS start_year_calendar_ids,
    arches_util.a2csv(r.archaeological_data -> 'chronology', 'end_year', ' | ') AS end_year,
    arches_util.a2csv_nested(r.archaeological_data -> 'chronology', 'end_year_qualifier', 'label', ' | ', '; ') AS end_year_qualifier,
    arches_util.a2csv_nested(r.archaeological_data -> 'chronology', 'end_year_qualifier', 'list_item_id', ' | ', '; ') AS end_year_qualifier_ids,
    arches_util.a2csv_nested(r.archaeological_data -> 'chronology', 'end_year_calendar', 'label', ' | ', '; ') AS end_year_calendar,
    arches_util.a2csv_nested(r.archaeological_data -> 'chronology', 'end_year_calendar', 'list_item_id', ' | ', '; ') AS end_year_calendar_ids,
    arches_util.a2csv_nested(r.archaeological_data -> 'chronology', 'determination_method', 'label', ' | ', '; ') AS determination_method,
    arches_util.a2csv_nested(r.archaeological_data -> 'chronology', 'determination_method', 'list_item_id', ' | ', '; ') AS determination_method_ids,
    arches_util.a2csv(r.archaeological_data -> 'chronology', 'information_source', ' | ') AS information_source,
    arches_util.a2csv(r.archaeological_data -> 'chronology', 'chronology_remarks', ' | ') AS chronology_remarks,
    jsonb_array_length(arches_util.as_array(r.archaeological_data -> 'chronology')) AS chronology_count,
    arches_util.a2csv_nested(r.archaeological_data -> 'archaeological_culture', 'archaeological_culture', 'label', ' | ', '; ') AS archaeological_culture,
    arches_util.a2csv_nested(r.archaeological_data -> 'archaeological_culture', 'archaeological_culture', 'list_item_id', ' | ', '; ') AS archaeological_culture_ids,
    arches_util.a2csv(r.archaeological_data -> 'archaeological_culture', 'culture_remarks', ' | ') AS culture_remarks,
    jsonb_array_length(arches_util.as_array(r.archaeological_data -> 'archaeological_culture')) AS archaeological_culture_count,
    arches_util.a2csv_nested(r.archaeological_data -> 'site_disturbance', 'disturbance_period', 'label', ' | ', '; ') AS disturbance_period,
    arches_util.a2csv_nested(r.archaeological_data -> 'site_disturbance', 'disturbance_period', 'list_item_id', ' | ', '; ') AS disturbance_period_ids,
    arches_util.a2csv_nested(r.archaeological_data -> 'site_disturbance', 'disturbance_cause', 'label', ' | ', '; ') AS disturbance_cause,
    arches_util.a2csv_nested(r.archaeological_data -> 'site_disturbance', 'disturbance_cause', 'list_item_id', ' | ', '; ') AS disturbance_cause_ids,
    arches_util.a2csv(r.archaeological_data -> 'site_disturbance', 'disturbance_remarks', ' | ') AS disturbance_remarks,
    jsonb_array_length(arches_util.as_array(r.archaeological_data -> 'site_disturbance')) AS site_disturbance_count,
    arches_util.a2csv_nested(r.archaeological_data -> 'additional_site_typology', 'typology_class', 'label', ' | ', '; ') AS typology_class,
    arches_util.a2csv_nested(r.archaeological_data -> 'additional_site_typology', 'typology_class', 'list_item_id', ' | ', '; ') AS typology_class_ids,
    arches_util.a2csv(r.archaeological_data -> 'additional_site_typology', 'typology_remark', ' | ') AS typology_remark,
    jsonb_array_length(arches_util.as_array(r.archaeological_data -> 'additional_site_typology')) AS additional_site_typology_count,
    arches_util.a2csv(r.remarks_and_recommendations -> 'recommendation', 'recorders_recommendation', ' | ') AS recorders_recommendation,
    arches_util.a2csv(r.remarks_and_recommendations -> 'recommendation', 'archaeology_branch_recommendation', ' | ') AS archaeology_branch_recommendation,
    jsonb_array_length(arches_util.as_array(r.remarks_and_recommendations -> 'recommendation')) AS recommendation_count,
    arches_util.a2csv(r.remarks_and_recommendations -> 'general_remark', 'remark', ' | ') AS remark,
    arches_util.a2csv(r.remarks_and_recommendations -> 'general_remark', 'remark_date', ' | ') AS remark_date,
    arches_util.a2csv_nested(r.remarks_and_recommendations -> 'general_remark', 'remark_source', 'label', ' | ', '; ') AS remark_source,
    arches_util.a2csv_nested(r.remarks_and_recommendations -> 'general_remark', 'remark_source', 'list_item_id', ' | ', '; ') AS remark_source_ids,
    jsonb_array_length(arches_util.as_array(r.remarks_and_recommendations -> 'general_remark')) AS general_remark_count,
    arches_util.a2csv_nested(r.related_documents -> 'related_site_documents', 'related_site_documents', 'name', ' | ', '; ') AS related_site_documents,
    arches_util.a2csv_nested(r.related_documents -> 'related_site_documents', 'related_site_documents', 'file_id', ' | ', '; ') AS related_site_documents_file_ids,
    arches_util.a2csv_nested(r.related_documents -> 'related_site_documents', 'related_document_type', 'label', ' | ', '; ') AS related_document_type,
    arches_util.a2csv_nested(r.related_documents -> 'related_site_documents', 'related_document_type', 'list_item_id', ' | ', '; ') AS related_document_type_ids,
    arches_util.a2csv(r.related_documents -> 'related_site_documents', 'related_document_description', ' | ') AS related_document_description,
    jsonb_array_length(arches_util.as_array(r.related_documents -> 'related_site_documents')) AS related_site_documents_count,
    arches_util.resource_names_nested(r.related_documents -> 'publication_reference', 'publication_reference', ' | ', '; ') AS publication_reference,
    arches_util.a2csv_nested(r.related_documents -> 'publication_reference', 'publication_reference', NULL, ' | ', '; ') AS publication_reference_ids,
    jsonb_array_length(arches_util.as_array(r.related_documents -> 'publication_reference')) AS publication_reference_count,
    arches_util.a2csv_nested(r.related_documents -> 'site_images', 'site_images', 'name', ' | ', '; ') AS site_images,
    arches_util.a2csv_nested(r.related_documents -> 'site_images', 'site_images', 'file_id', ' | ', '; ') AS site_images_file_ids,
    arches_util.a2csv(r.related_documents -> 'site_images', 'primary_image', ' | ') AS primary_image,
    arches_util.a2csv_nested(r.related_documents -> 'site_images', 'image_type', 'label', ' | ', '; ') AS image_type,
    arches_util.a2csv_nested(r.related_documents -> 'site_images', 'image_type', 'list_item_id', ' | ', '; ') AS image_type_ids,
    arches_util.a2csv_nested(r.related_documents -> 'site_images', 'image_view', 'label', ' | ', '; ') AS image_view,
    arches_util.a2csv_nested(r.related_documents -> 'site_images', 'image_view', 'list_item_id', ' | ', '; ') AS image_view_ids,
    arches_util.a2csv(r.related_documents -> 'site_images', 'image_description', ' | ') AS image_description,
    arches_util.a2csv(r.related_documents -> 'site_images', 'image_features', ' | ') AS image_features,
    arches_util.a2csv(r.related_documents -> 'site_images', 'photographer', ' | ') AS photographer,
    arches_util.a2csv(r.related_documents -> 'site_images', 'copyright', ' | ') AS copyright,
    arches_util.a2csv(r.related_documents -> 'site_images', 'image_date', ' | ') AS image_date,
    jsonb_array_length(arches_util.as_array(r.related_documents -> 'site_images')) AS site_images_count,
    arches_util.a2csv_nested(r.ancestral_remains, 'ancestral_remains_type', 'label', ' | ', '; ') AS ancestral_remains_type,
    arches_util.a2csv_nested(r.ancestral_remains, 'ancestral_remains_type', 'list_item_id', ' | ', '; ') AS ancestral_remains_type_ids,
    arches_util.a2csv_nested(r.ancestral_remains, 'ancestral_remains_status', 'label', ' | ', '; ') AS ancestral_remains_status,
    arches_util.a2csv_nested(r.ancestral_remains, 'ancestral_remains_status', 'list_item_id', ' | ', '; ') AS ancestral_remains_status_ids,
    arches_util.a2csv(r.ancestral_remains, 'ancestral_remains_remarks', ' | ') AS ancestral_remains_remarks,
    arches_util.resource_name_col(r.ancestral_remains, 'ancestral_remains_repository', ' | ') AS ancestral_remains_repository,
    arches_util.a2csv(r.ancestral_remains, 'ancestral_remains_repository', ' | ') AS ancestral_remains_repository_ids,
    arches_util.a2csv(r.ancestral_remains, 'minimum_number_of_individuals', ' | ') AS minimum_number_of_individuals,
    arches_util.a2csv(r.ancestral_remains, 'multiple_burials', ' | ') AS multiple_burials,
    jsonb_array_length(arches_util.as_array(r.ancestral_remains)) AS ancestral_remains_count,
    arches_util.a2csv_nested(r.site_visit_location, 'boundary_type', 'label', ' | ', '; ') AS boundary_type,
    arches_util.a2csv_nested(r.site_visit_location, 'boundary_type', 'list_item_id', ' | ', '; ') AS boundary_type_ids,
    arches_util.a2csv_nested(r.site_visit_location, 'latest_edit_type', 'label', ' | ', '; ') AS latest_edit_type,
    arches_util.a2csv_nested(r.site_visit_location, 'latest_edit_type', 'list_item_id', ' | ', '; ') AS latest_edit_type_ids,
    arches_util.a2csv(r.site_visit_location, 'location_and_access', ' | ') AS location_and_access,
    arches_util.a2csv(r.site_visit_location, 'accuracy_remarks', ' | ') AS accuracy_remarks,
    jsonb_array_length(arches_util.as_array(r.site_visit_location)) AS site_visit_location_count,
    arches_util.path_csv(r.site_visit_location, '$[*].biogeography[*].biogeography_name', ' | ') AS biogeography_name,
    arches_util.path_csv(r.site_visit_location, '$[*].biogeography[*].biogeography_description', ' | ') AS biogeography_description,
    arches_util.path_csv(r.site_visit_location, '$[*].biogeography[*].biogeography_type[*].label', ' | ') AS biogeography_type,
    arches_util.path_csv(r.site_visit_location, '$[*].biogeography[*].biogeography_type[*].list_item_id', ' | ') AS biogeography_type_ids,
    (SELECT count(*) FROM jsonb_path_query(r.site_visit_location, '$[*].biogeography[*]'))::int AS biogeography_count
FROM site_visit.mv_resource_v1 r;

CREATE UNIQUE INDEX mv_resource_flat_v1_pk
    ON site_visit.mv_resource_flat_v1 (resourceinstanceid);
CREATE INDEX mv_resource_flat_v1_geom
    ON site_visit.mv_resource_flat_v1 USING GIST (site_visit_geom);


-- ---------------------------------------------------------------------
-- Wrapper view. Same pattern as site_visit.resource: downstream names THIS,
-- never the matview, so you can rebuild the backing matview and repoint.
-- ---------------------------------------------------------------------
-- Column list filtered and ordered to match the DataBC export spec.
-- Excluded: all _ids / _count columns; NO fields (site_form_authors,
--   first_date_of_site_visit); boundary_type (not in spec); centroid_lat/lon.
-- site_name: view deliberately avoids the bare `name` alias; spreadsheet
--   lists the field as `name` - confirm whether to rename here.
-- site_visit_geom: PostGIS geometry, aliased to site_visit_location per spec.
--   Spec type is geojson-feature-collection; this column is a geometry, not
--   a GeoJSON text string - downstream tools must cast/transform as needed.
-- recommended_unprotected_areas: NO? in spec and not present in matview.
CREATE OR REPLACE VIEW site_visit.resource_flat AS
SELECT
    resourceinstanceid,
    -- Site Visit Details
    site_visit_type,
    is_site_visit_permitted,
    last_date_of_site_visit,
    project_description,
    associated_permit,
    archaeological_site,
    affiliation,
    -- Site Visit Location
    site_visit_geom                         AS site_visit_location,
    location_and_access,
    latest_edit_type,
    accuracy_remarks,
    -- Biogeography
    biogeography_type,
    biogeography_description,
    biogeography_name,
    -- Additional Site Typology
    typology_class,
    typology_remark,
    -- Ancestral Remains
    ancestral_remains_type,
    multiple_burials,
    ancestral_remains_status,
    ancestral_remains_remarks,
    minimum_number_of_individuals,
    ancestral_remains_repository,
    -- Archaeological Culture
    culture_remarks,
    archaeological_culture,
    -- Archaeological Feature
    feature_count,
    archaeological_feature,
    feature_remarks,
    -- Chronology (order matches spec)
    end_year_calendar,
    end_year_qualifier,
    start_year,
    determination_method,
    chronology_remarks,
    information_source,
    end_year,
    start_year_calendar,
    start_year_qualifier,
    -- Cultural Material
    cultural_material_type,
    cultural_material_status,
    cultural_material_details,
    number_of_artifacts,
    repository,
    -- General Remark
    remark_source,
    remark_date,
    remark,
    -- New Site Names (spreadsheet alias is `name`; see note above)
    name_type,
    site_name,
    assigned_or_reported_by,
    name_remarks,
    assigned_or_reported_date,
    -- Publication Reference
    publication_reference,
    -- Recommendation
    recorders_recommendation,
    archaeology_branch_recommendation,
    -- Related Site Documents
    related_document_type,
    related_document_description,
    related_site_documents,
    -- Site Disturbance
    disturbance_period,
    disturbance_cause,
    disturbance_remarks,
    -- Site Images
    primary_image,
    image_type,
    photographer,
    site_images,
    image_view,
    image_description,
    copyright,
    image_date,
    image_features,
    -- Stratigraphy
    stratigraphy,
    -- Team Member
    member_roles,
    team_member,
    was_on_site,
    -- Temporary Number
    temporary_number,
    temporary_number_assigned_by,
    temporary_number_assigned_date
FROM site_visit.mv_resource_flat_v1;

COMMENT ON VIEW site_visit.resource_flat IS
'Flat denormalized site_visit records, one row per resource. Cardinality-n values are '
'delimiter-joined text: " | " between tiles, "; " within a tile. Sibling columns from the '
'same nodegroup are POSITIONALLY ALIGNED - empty slots are meaningful, do not strip them. '
'Lossy and one-way; site_visit.resource is the round-trippable object.';

COMMENT ON COLUMN site_visit.mv_resource_flat_v1.biogeography_name IS
'Flattened across ALL site_visit_location tiles. Aligns with the other biogeography_* '
'columns, but NOT with boundary_type / location_and_access / accuracy_remarks.';
COMMENT ON COLUMN site_visit.mv_resource_flat_v1.biogeography_type IS
'Flattened across ALL site_visit_location tiles - see biogeography_name.';

-- GRANT SELECT ON site_visit.resource_flat TO <app_role>;
select * from  site_visit.mv_resource_flat_v1;


-- ---------------------------------------------------------------------
-- Refresh. MUST run after mv_resource_v1 - it reads from it.
-- ---------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE site_visit.refresh_resource_flat(concurrent boolean DEFAULT true)
LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE format('REFRESH MATERIALIZED VIEW %s site_visit.mv_resource_flat_v1',
                   CASE WHEN concurrent THEN 'CONCURRENTLY' ELSE '' END);
END $$;
-- Append this to site_visit.refresh_resource()'s array, AFTER mv_resource_v1,
-- or call it straight after. It is the last link in the chain.


-- =====================================================================
-- ALIGNMENT REGRESSION TEST  (v2 - the v1 version was BROKEN, see below)
--
-- WHY v1 REPORTED FALSE POSITIVES:
--     array_length(string_to_array('', ' | '), 1)  =  NULL,  not 1.
-- Postgres returns an EMPTY ARRAY for string_to_array on an empty string. So a
-- resource with ONE tile whose field is empty produced a column value of '',
-- which counted as NULL slots instead of 1, and got flagged. Single-tile records
-- with empty optional fields are the common case - which is exactly why
-- chronology and cultural_material lit up in the thousands while site_images,
-- where photographer/copyright/description are usually filled, showed only 9.
--
-- nslots() counts delimiters instead, so '' correctly counts as one slot.
--
-- Misalignment is in fact STRUCTURALLY IMPOSSIBLE with these helpers: a2csv and
-- a2csv_nested both walk every element of the array with COALESCE(..., ''), so
-- they emit exactly one slot per tile, always. This test exists to catch a future
-- edit that breaks that invariant - e.g. someone "tidying up" the empty slots.
--
-- biogeography_* is excluded on purpose: it is three levels deep and flattens
-- across location tiles, so it is NOT aligned to its siblings. Documented.
-- =====================================================================

CREATE OR REPLACE FUNCTION arches_util.nslots(s text, delim text DEFAULT ' | ')
RETURNS int LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE WHEN s IS NULL THEN 0
           ELSE (length(s) - length(replace(s, delim, ''))) / length(delim) + 1 END;
$$;

WITH v AS (
  SELECT resourceinstanceid, team_member_count AS n, 'team_member' AS grp,
         ARRAY[arches_util.nslots(team_member),
             arches_util.nslots(team_member_ids),
             arches_util.nslots(member_roles),
             arches_util.nslots(member_roles_ids),
             arches_util.nslots(was_on_site)] AS slots,
         ARRAY['team_member', 'team_member_ids', 'member_roles', 'member_roles_ids', 'was_on_site']::text[] AS colnames
  FROM site_visit.resource_flat WHERE team_member_count > 0
  UNION ALL
  SELECT resourceinstanceid, new_site_names_count AS n, 'new_site_names' AS grp,
         ARRAY[arches_util.nslots(site_name),
             arches_util.nslots(name_type),
             arches_util.nslots(name_type_ids),
             arches_util.nslots(name_remarks),
             arches_util.nslots(assigned_or_reported_by),
             arches_util.nslots(assigned_or_reported_by_ids),
             arches_util.nslots(assigned_or_reported_date)] AS slots,
         ARRAY['site_name', 'name_type', 'name_type_ids', 'name_remarks', 'assigned_or_reported_by', 'assigned_or_reported_by_ids', 'assigned_or_reported_date']::text[] AS colnames
  FROM site_visit.resource_flat WHERE new_site_names_count > 0
  UNION ALL
  SELECT resourceinstanceid, cultural_material_count AS n, 'cultural_material' AS grp,
         ARRAY[arches_util.nslots(cultural_material_type),
             arches_util.nslots(cultural_material_type_ids),
             arches_util.nslots(cultural_material_status),
             arches_util.nslots(cultural_material_status_ids),
             arches_util.nslots(cultural_material_details),
             arches_util.nslots(number_of_artifacts),
             arches_util.nslots(repository),
             arches_util.nslots(repository_ids)] AS slots,
         ARRAY['cultural_material_type', 'cultural_material_type_ids', 'cultural_material_status', 'cultural_material_status_ids', 'cultural_material_details', 'number_of_artifacts', 'repository', 'repository_ids']::text[] AS colnames
  FROM site_visit.resource_flat WHERE cultural_material_count > 0
  UNION ALL
  SELECT resourceinstanceid, stratigraphy_count AS n, 'stratigraphy' AS grp,
         ARRAY[arches_util.nslots(stratigraphy)] AS slots,
         ARRAY['stratigraphy']::text[] AS colnames
  FROM site_visit.resource_flat WHERE stratigraphy_count > 0
  UNION ALL
  SELECT resourceinstanceid, archaeological_feature_count AS n, 'archaeological_feature' AS grp,
         ARRAY[arches_util.nslots(archaeological_feature),
             arches_util.nslots(archaeological_feature_ids),
             arches_util.nslots(feature_count),
             arches_util.nslots(feature_remarks)] AS slots,
         ARRAY['archaeological_feature', 'archaeological_feature_ids', 'feature_count', 'feature_remarks']::text[] AS colnames
  FROM site_visit.resource_flat WHERE archaeological_feature_count > 0
  UNION ALL
  SELECT resourceinstanceid, chronology_count AS n, 'chronology' AS grp,
         ARRAY[arches_util.nslots(start_year),
             arches_util.nslots(start_year_qualifier),
             arches_util.nslots(start_year_qualifier_ids),
             arches_util.nslots(start_year_calendar),
             arches_util.nslots(start_year_calendar_ids),
             arches_util.nslots(end_year),
             arches_util.nslots(end_year_qualifier),
             arches_util.nslots(end_year_qualifier_ids),
             arches_util.nslots(end_year_calendar),
             arches_util.nslots(end_year_calendar_ids),
             arches_util.nslots(determination_method),
             arches_util.nslots(determination_method_ids),
             arches_util.nslots(information_source),
             arches_util.nslots(chronology_remarks)] AS slots,
         ARRAY['start_year', 'start_year_qualifier', 'start_year_qualifier_ids', 'start_year_calendar', 'start_year_calendar_ids', 'end_year', 'end_year_qualifier', 'end_year_qualifier_ids', 'end_year_calendar', 'end_year_calendar_ids', 'determination_method', 'determination_method_ids', 'information_source', 'chronology_remarks']::text[] AS colnames
  FROM site_visit.resource_flat WHERE chronology_count > 0
  UNION ALL
  SELECT resourceinstanceid, archaeological_culture_count AS n, 'archaeological_culture' AS grp,
         ARRAY[arches_util.nslots(archaeological_culture),
             arches_util.nslots(archaeological_culture_ids),
             arches_util.nslots(culture_remarks)] AS slots,
         ARRAY['archaeological_culture', 'archaeological_culture_ids', 'culture_remarks']::text[] AS colnames
  FROM site_visit.resource_flat WHERE archaeological_culture_count > 0
  UNION ALL
  SELECT resourceinstanceid, site_disturbance_count AS n, 'site_disturbance' AS grp,
         ARRAY[arches_util.nslots(disturbance_period),
             arches_util.nslots(disturbance_period_ids),
             arches_util.nslots(disturbance_cause),
             arches_util.nslots(disturbance_cause_ids),
             arches_util.nslots(disturbance_remarks)] AS slots,
         ARRAY['disturbance_period', 'disturbance_period_ids', 'disturbance_cause', 'disturbance_cause_ids', 'disturbance_remarks']::text[] AS colnames
  FROM site_visit.resource_flat WHERE site_disturbance_count > 0
  UNION ALL
  SELECT resourceinstanceid, additional_site_typology_count AS n, 'additional_site_typology' AS grp,
         ARRAY[arches_util.nslots(typology_class),
             arches_util.nslots(typology_class_ids),
             arches_util.nslots(typology_remark)] AS slots,
         ARRAY['typology_class', 'typology_class_ids', 'typology_remark']::text[] AS colnames
  FROM site_visit.resource_flat WHERE additional_site_typology_count > 0
  UNION ALL
  SELECT resourceinstanceid, recommendation_count AS n, 'recommendation' AS grp,
         ARRAY[arches_util.nslots(recorders_recommendation),
             arches_util.nslots(archaeology_branch_recommendation)] AS slots,
         ARRAY['recorders_recommendation', 'archaeology_branch_recommendation']::text[] AS colnames
  FROM site_visit.resource_flat WHERE recommendation_count > 0
  UNION ALL
  SELECT resourceinstanceid, general_remark_count AS n, 'general_remark' AS grp,
         ARRAY[arches_util.nslots(remark),
             arches_util.nslots(remark_date),
             arches_util.nslots(remark_source),
             arches_util.nslots(remark_source_ids)] AS slots,
         ARRAY['remark', 'remark_date', 'remark_source', 'remark_source_ids']::text[] AS colnames
  FROM site_visit.resource_flat WHERE general_remark_count > 0
  UNION ALL
  SELECT resourceinstanceid, related_site_documents_count AS n, 'related_site_documents' AS grp,
         ARRAY[arches_util.nslots(related_site_documents),
             arches_util.nslots(related_site_documents_file_ids),
             arches_util.nslots(related_document_type),
             arches_util.nslots(related_document_type_ids),
             arches_util.nslots(related_document_description)] AS slots,
         ARRAY['related_site_documents', 'related_site_documents_file_ids', 'related_document_type', 'related_document_type_ids', 'related_document_description']::text[] AS colnames
  FROM site_visit.resource_flat WHERE related_site_documents_count > 0
  UNION ALL
  SELECT resourceinstanceid, publication_reference_count AS n, 'publication_reference' AS grp,
         ARRAY[arches_util.nslots(publication_reference),
             arches_util.nslots(publication_reference_ids)] AS slots,
         ARRAY['publication_reference', 'publication_reference_ids']::text[] AS colnames
  FROM site_visit.resource_flat WHERE publication_reference_count > 0
  UNION ALL
  SELECT resourceinstanceid, site_images_count AS n, 'site_images' AS grp,
         ARRAY[arches_util.nslots(site_images),
             arches_util.nslots(site_images_file_ids),
             arches_util.nslots(primary_image),
             arches_util.nslots(image_type),
             arches_util.nslots(image_type_ids),
             arches_util.nslots(image_view),
             arches_util.nslots(image_view_ids),
             arches_util.nslots(image_description),
             arches_util.nslots(image_features),
             arches_util.nslots(photographer),
             arches_util.nslots(copyright),
             arches_util.nslots(image_date)] AS slots,
         ARRAY['site_images', 'site_images_file_ids', 'primary_image', 'image_type', 'image_type_ids', 'image_view', 'image_view_ids', 'image_description', 'image_features', 'photographer', 'copyright', 'image_date']::text[] AS colnames
  FROM site_visit.resource_flat WHERE site_images_count > 0
  UNION ALL
  SELECT resourceinstanceid, ancestral_remains_count AS n, 'ancestral_remains' AS grp,
         ARRAY[arches_util.nslots(ancestral_remains_type),
             arches_util.nslots(ancestral_remains_type_ids),
             arches_util.nslots(ancestral_remains_status),
             arches_util.nslots(ancestral_remains_status_ids),
             arches_util.nslots(ancestral_remains_remarks),
             arches_util.nslots(ancestral_remains_repository),
             arches_util.nslots(ancestral_remains_repository_ids),
             arches_util.nslots(minimum_number_of_individuals),
             arches_util.nslots(multiple_burials)] AS slots,
         ARRAY['ancestral_remains_type', 'ancestral_remains_type_ids', 'ancestral_remains_status', 'ancestral_remains_status_ids', 'ancestral_remains_remarks', 'ancestral_remains_repository', 'ancestral_remains_repository_ids', 'minimum_number_of_individuals', 'multiple_burials']::text[] AS colnames
  FROM site_visit.resource_flat WHERE ancestral_remains_count > 0
  UNION ALL
  SELECT resourceinstanceid, site_visit_location_count AS n, 'site_visit_location' AS grp,
         ARRAY[arches_util.nslots(boundary_type),
             arches_util.nslots(boundary_type_ids),
             arches_util.nslots(latest_edit_type),
             arches_util.nslots(latest_edit_type_ids),
             arches_util.nslots(location_and_access),
             arches_util.nslots(accuracy_remarks)] AS slots,
         ARRAY['boundary_type', 'boundary_type_ids', 'latest_edit_type', 'latest_edit_type_ids', 'location_and_access', 'accuracy_remarks']::text[] AS colnames
  FROM site_visit.resource_flat WHERE site_visit_location_count > 0
)
SELECT grp, colname,
       count(DISTINCT resourceinstanceid) AS rows_affected,
       count(*)                           AS bad_cells
FROM v, LATERAL unnest(slots, colnames) AS u(sl, colname)
WHERE sl IS DISTINCT FROM n
GROUP BY grp, colname
ORDER BY rows_affected DESC, grp, colname;
-- Expect ZERO ROWS. Any row names the exact column that desynchronized.