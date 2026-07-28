-- DataBC export views for the Site Visit resource model.
-- Sources: site_visit.resource_flat, .site_visit_location_flat
--
-- Rules applied for Oracle compatibility:
--   * resourceinstanceid cast to text
--   * All text columns wrapped with LEFT(col, 4000)
--   * Reference _ids columns removed (internal list-item UUIDs)
--   * File _ids columns removed (not resource links)
--   * resource-instance and resource-instance-list _id/_ids retained as join keys
--
-- Two views are created:
--   databc.vw_site_visit          — one row per site visit
--   databc.vw_site_visit_location — one row per site_visit_location tile
--
-- Join path:
--   vw_site_visit                 ON resourceinstanceid
--   -> vw_site_visit_location     ON resourceinstanceid, site_visit_location_index
--
-- site_visit_location_geom is the combined PostGIS geometry for all location
-- tiles; per-tile text attributes live in vw_site_visit_location.

CREATE SCHEMA IF NOT EXISTS databc;

-- ============================================================
-- 1. Main resource-level view
-- ============================================================
CREATE OR REPLACE VIEW databc.vw_site_visit AS
SELECT
    resourceinstanceid::text                        AS resourceinstanceid,

    -- Site Visit Location (resource-level combined geometry)
    site_visit_location_geom,                                               -- geometry

    -- Site Visit Details
    is_site_visit_permitted,                                                -- boolean
    LEFT(site_visit_type, 4000)                     AS site_visit_type,
    last_date_of_site_visit,                                                -- date
    LEFT(project_description, 4000)                 AS project_description,
    LEFT(associated_permit, 4000)                   AS associated_permit,
    LEFT(associated_permit_ids, 4000)               AS associated_permit_ids,           -- resource-instance-list
    LEFT(archaeological_site, 4000)                 AS archaeological_site,
    LEFT(archaeological_site_id, 4000)              AS archaeological_site_id,          -- resource-instance
    LEFT(affiliation, 4000)                         AS affiliation,
    LEFT(affiliation_id, 4000)                      AS affiliation_id,                  -- resource-instance

    -- Temporary Number
    LEFT(temporary_number, 4000)                    AS temporary_number,
    LEFT(temporary_number_assigned_by, 4000)        AS temporary_number_assigned_by,
    LEFT(temporary_number_assigned_by_id, 4000)     AS temporary_number_assigned_by_id, -- resource-instance
    temporary_number_assigned_date,                                         -- date

    -- New Site Names
    LEFT(name, 4000)                                AS name,
    LEFT(name_type, 4000)                           AS name_type,
    LEFT(name_remarks, 4000)                        AS name_remarks,
    LEFT(assigned_or_reported_by, 4000)             AS assigned_or_reported_by,
    LEFT(assigned_or_reported_by_ids, 4000)         AS assigned_or_reported_by_ids,     -- resource-instance
    LEFT(assigned_or_reported_date, 4000)           AS assigned_or_reported_date,

    -- Ancestral Remains
    LEFT(ancestral_remains_type, 4000)              AS ancestral_remains_type,
    LEFT(multiple_burials, 4000)                    AS multiple_burials,
    LEFT(ancestral_remains_status, 4000)            AS ancestral_remains_status,
    LEFT(ancestral_remains_remarks, 4000)           AS ancestral_remains_remarks,
    LEFT(minimum_number_of_individuals, 4000)       AS minimum_number_of_individuals,
    LEFT(ancestral_remains_repository, 4000)        AS ancestral_remains_repository,
    LEFT(ancestral_remains_repository_ids, 4000)    AS ancestral_remains_repository_ids, -- resource-instance

    -- Cultural Material
    LEFT(cultural_material_type, 4000)              AS cultural_material_type,
    LEFT(cultural_material_status, 4000)            AS cultural_material_status,
    LEFT(cultural_material_details, 4000)           AS cultural_material_details,
    LEFT(number_of_artifacts, 4000)                 AS number_of_artifacts,
    LEFT(repository, 4000)                          AS repository,
    LEFT(repository_ids, 4000)                      AS repository_ids,                  -- resource-instance

    -- Stratigraphy
    LEFT(stratigraphy, 4000)                        AS stratigraphy,

    -- Archaeological Feature
    LEFT(archaeological_feature, 4000)              AS archaeological_feature,
    LEFT(feature_count, 4000)                       AS feature_count,
    LEFT(feature_remarks, 4000)                     AS feature_remarks,

    -- Chronology
    LEFT(start_year, 4000)                          AS start_year,
    LEFT(start_year_calendar, 4000)                 AS start_year_calendar,
    LEFT(start_year_qualifier, 4000)                AS start_year_qualifier,
    LEFT(end_year, 4000)                            AS end_year,
    LEFT(end_year_calendar, 4000)                   AS end_year_calendar,
    LEFT(end_year_qualifier, 4000)                  AS end_year_qualifier,
    LEFT(determination_method, 4000)                AS determination_method,
    LEFT(information_source, 4000)                  AS information_source,
    LEFT(chronology_remarks, 4000)                  AS chronology_remarks,

    -- Archaeological Culture
    LEFT(archaeological_culture, 4000)              AS archaeological_culture,
    LEFT(culture_remarks, 4000)                     AS culture_remarks,

    -- Site Disturbance
    LEFT(disturbance_period, 4000)                  AS disturbance_period,
    LEFT(disturbance_cause, 4000)                   AS disturbance_cause,
    LEFT(disturbance_remarks, 4000)                 AS disturbance_remarks,

    -- Additional Site Typology
    LEFT(typology_class, 4000)                      AS typology_class,
    LEFT(typology_remark, 4000)                     AS typology_remark,

    -- Recommendation
    LEFT(recorders_recommendation, 4000)            AS recorders_recommendation,
    LEFT(archaeology_branch_recommendation, 4000)   AS archaeology_branch_recommendation,

    -- General Remark
    LEFT(remark, 4000)                              AS remark,
    LEFT(remark_source, 4000)                       AS remark_source,
    LEFT(remark_date, 4000)                         AS remark_date,

    -- Publication Reference
    LEFT(publication_reference, 4000)               AS publication_reference,
    LEFT(publication_reference_ids, 4000)           AS publication_reference_ids,       -- resource-instance-list

    -- Related Site Documents
    LEFT(related_site_documents, 4000)              AS related_site_documents,
    LEFT(related_document_type, 4000)               AS related_document_type,
    LEFT(related_document_description, 4000)        AS related_document_description,

    -- Site Images
    LEFT(site_images, 4000)                         AS site_images,
    LEFT(primary_image, 4000)                       AS primary_image,
    LEFT(image_type, 4000)                          AS image_type,
    LEFT(image_view, 4000)                          AS image_view,
    LEFT(image_description, 4000)                   AS image_description,
    LEFT(image_features, 4000)                      AS image_features,
    LEFT(photographer, 4000)                        AS photographer,
    LEFT(copyright, 4000)                           AS copyright,
    LEFT(image_date, 4000)                          AS image_date,

    -- Team Member
    LEFT(team_member, 4000)                         AS team_member,
    LEFT(team_member_ids, 4000)                     AS team_member_ids,                 -- resource-instance
    LEFT(member_roles, 4000)                        AS member_roles,
    LEFT(was_on_site, 4000)                         AS was_on_site

FROM site_visit.resource_flat;

COMMENT ON VIEW databc.vw_site_visit IS
'DataBC export subset for the Site Visit resource model. '
'One row per site visit. All text columns capped at 4000 chars for Oracle. '
'Per-tile location attributes are in companion view vw_site_visit_location.';


-- ============================================================
-- 2. Site Visit Location grain view (one row per location tile)
-- ============================================================
CREATE OR REPLACE VIEW databc.vw_site_visit_location AS
SELECT
    resourceinstanceid::text                        AS resourceinstanceid,
    site_visit_location_index,                                              -- integer join key

    -- Site Visit Location attributes
    LEFT(location_and_access, 4000)                 AS location_and_access,
    LEFT(latest_edit_type, 4000)                    AS latest_edit_type,
    LEFT(accuracy_remarks, 4000)                    AS accuracy_remarks,

    -- Biogeography
    LEFT(biogeography_type, 4000)                   AS biogeography_type,
    LEFT(biogeography_name, 4000)                   AS biogeography_name,
    LEFT(biogeography_description, 4000)            AS biogeography_description

FROM site_visit.site_visit_location_flat;

COMMENT ON VIEW databc.vw_site_visit_location IS
'DataBC export subset for Site Visit site_visit_location tiles. '
'One row per location occurrence. '
'Join to vw_site_visit on resourceinstanceid.';


-- ============================================================
-- Text-length validation
-- ============================================================
DO $$
DECLARE
    r     record;
    v_max bigint;
    src   text;
    vw    text;
BEGIN
    FOR src, vw IN VALUES
        ('resource_flat',              'vw_site_visit'),
        ('site_visit_location_flat',   'vw_site_visit_location')
    LOOP
        FOR r IN
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'site_visit'
              AND table_name   = src
              AND data_type    = 'text'
            ORDER BY ordinal_position
        LOOP
            EXECUTE format(
                $q$SELECT max(length(%I)) FROM site_visit.%I$q$,
                r.column_name, src
            ) INTO v_max;
            IF v_max IS NOT NULL AND v_max > 4000 THEN
                RAISE WARNING
                    'site_visit.%.% max length = % — truncated in databc.%',
                    src, r.column_name, v_max, vw;
            END IF;
        END LOOP;
        RAISE NOTICE 'Length check complete for site_visit.%', src;
    END LOOP;
END $$;
