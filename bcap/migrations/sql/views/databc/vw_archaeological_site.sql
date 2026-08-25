-- DataBC export views for the Archaeological Site resource model.
-- Sources: archaeological_site.resource_flat, .site_location_flat,
--          .bc_property_address_flat
--
-- Rules applied for Oracle compatibility:
--   * resourceinstanceid cast to text
--   * All text columns wrapped with LEFT(col, 4000)
--   * Reference/concept _ids columns removed (internal list-item UUIDs)
--   * File _ids columns removed (not resource links)
--   * resource-instance and resource-instance-list _id/_ids retained as join keys
--
-- Three views are created:
--   databc.vw_archaeological_site              — one row per site
--   databc.vw_archaeological_site_site_location — one row per site_location tile
--   databc.vw_archaeological_site_bc_property_address — one row per address tile
--
-- Join path:
--   vw_archaeological_site                          ON resourceinstanceid
--   -> vw_archaeological_site_site_location         ON resourceinstanceid,
--                                                      site_location_index
--   -> vw_archaeological_site_bc_property_address   ON resourceinstanceid,
--                                                      site_location_index,
--                                                      bc_property_address_index
--
-- NOTE: responsible_government and authority_legal_instrument are in the data
-- model but absent from the current flat view — add to databc_config.py flat_grains
-- or ensure the nodes are included in the generated MV to expose them.

CREATE SCHEMA IF NOT EXISTS databc;

-- ============================================================
-- 1. Main resource-level view
-- ============================================================
CREATE OR REPLACE VIEW databc.vw_archaeological_site AS
SELECT
    resourceinstanceid::text                        AS resourceinstanceid,

    -- Site Boundary geometry (union of all boundary tiles)
    site_boundary_geom,                                                     -- geometry
    site_boundary_polygons,                                                 -- geometry (polygons only)

    -- Unprotected Areas geometry (union of all unprotected area tiles)
    unprotected_areas_geom,                                                 -- geometry
    unprotected_areas_polygons,                                             -- geometry (polygons only)

    -- Identification and Registration
    LEFT(borden_number, 4000)                       AS borden_number,
    LEFT(parcel_owner_type, 4000)                   AS parcel_owner_type,
    borden_number_issuance_date,                                            -- date
    LEFT(register_type, 4000)                       AS register_type,
    LEFT(parent_site, 4000)                         AS parent_site,
    LEFT(parent_site_id, 4000)                      AS parent_site_id,     -- resource-instance

    -- Authority
    LEFT(authority_start_date, 4000)                AS authority_start_date,
    LEFT(authority_end_date, 4000)                  AS authority_end_date,
    LEFT(legislative_act, 4000)                     AS legislative_act,
    LEFT(legislative_act_ids, 4000)                 AS legislative_act_ids, -- resource-instance
    LEFT(authority_protection_type, 4000)           AS authority_protection_type,
    LEFT(reference_number, 4000)                    AS reference_number,
    LEFT(authority_description, 4000)               AS authority_description,

    -- Site Boundary
    LEFT(site_boundary_description, 4000)           AS site_boundary_description,
    LEFT(accuracy_remarks, 4000)                    AS accuracy_remarks,
    LEFT(latest_edit_type, 4000)                    AS latest_edit_type,

    -- Site Decision
    LEFT(decision_registration_status, 4000)        AS decision_registration_status,

    -- Site Typology
    LEFT(typology_class, 4000)                      AS typology_class,
    LEFT(typology_remark, 4000)                     AS typology_remark,

    -- Site Names
    LEFT(name, 4000)                                AS name,
    LEFT(name_type, 4000)                           AS name_type,
    LEFT(name_remarks, 4000)                        AS name_remarks,
    LEFT(assigned_or_reported_by, 4000)             AS assigned_or_reported_by,
    LEFT(assigned_or_reported_by_ids, 4000)         AS assigned_or_reported_by_ids, -- resource-instance
    LEFT(assigned_or_reported_date, 4000)           AS assigned_or_reported_date,

    -- General Remark Information
    LEFT(general_remark, 4000)                      AS general_remark,
    LEFT(general_remark_source, 4000)               AS general_remark_source,
    LEFT(general_remark_date, 4000)                 AS general_remark_date,

    -- Remark Keyword
    LEFT(remark_keyword, 4000)                      AS remark_keyword,

    -- Publication Reference
    LEFT(publication_reference, 4000)               AS publication_reference,
    LEFT(publication_reference_ids, 4000)           AS publication_reference_ids, -- resource-instance-list

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
    LEFT(image_date, 4000)                          AS image_date

FROM archaeological_site.resource_flat;

COMMENT ON VIEW databc.vw_archaeological_site IS
'DataBC export subset for the Archaeological Site resource model. '
'One row per site. All text columns capped at 4000 chars for Oracle. '
'Site Location and BC Property Address grain data are in companion views '
'vw_archaeological_site_site_location and vw_archaeological_site_bc_property_address.';


-- ============================================================
-- 2. Site Location grain view (one row per site_location tile)
-- ============================================================
CREATE OR REPLACE VIEW databc.vw_archaeological_site_site_location AS
SELECT
    resourceinstanceid::text                        AS resourceinstanceid,
    site_location_index,                                                    -- integer join key

    -- Biogeography
    LEFT(biogeography_type, 4000)                   AS biogeography_type,
    LEFT(biogeography_name, 4000)                   AS biogeography_name,
    LEFT(biogeography_description, 4000)            AS biogeography_description,

    -- Elevation
    gis_lower_elevation,                                                    -- numeric
    gis_upper_elevation,                                                    -- numeric

    -- Elevation Comments
    LEFT(elevation_comments, 4000)                  AS elevation_comments,

    -- Site Tenure
    LEFT(site_tenure_remarks, 4000)                 AS site_tenure_remarks,
    LEFT(site_tenure_type, 4000)                    AS site_tenure_type,
    LEFT(site_tenure_identifier, 4000)              AS site_tenure_identifier

FROM archaeological_site.site_location_flat;

COMMENT ON VIEW databc.vw_archaeological_site_site_location IS
'DataBC export subset for Archaeological Site site_location tiles. '
'One row per site_location occurrence. '
'Join to vw_archaeological_site on resourceinstanceid.';


-- ============================================================
-- 3. BC Property Address grain view (one row per address tile)
-- ============================================================
CREATE OR REPLACE VIEW databc.vw_archaeological_site_bc_property_address AS
SELECT
    resourceinstanceid::text                        AS resourceinstanceid,
    site_location_index,                                                    -- integer join key
    bc_property_address_index,                                              -- integer join key

    -- BC Property Address
    LEFT(street_number, 4000)                       AS street_number,
    LEFT(street_name, 4000)                         AS street_name,
    LEFT(city, 4000)                                AS city,
    LEFT(postal_code, 4000)                         AS postal_code,
    LEFT(address_remarks, 4000)                     AS address_remarks,

    -- BC Property Legal Description
    LEFT(pid, 4000)                                 AS pid,
    LEFT(pin, 4000)                                 AS pin,
    LEFT(legal_description, 4000)                   AS legal_description,
    LEFT(legal_address_remarks, 4000)               AS legal_address_remarks

FROM archaeological_site.bc_property_address_flat;

COMMENT ON VIEW databc.vw_archaeological_site_bc_property_address IS
'DataBC export subset for Archaeological Site BC Property Address tiles. '
'One row per address within a site_location tile. '
'Join to vw_archaeological_site_site_location on (resourceinstanceid, site_location_index).';


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
        ('resource_flat',         'vw_archaeological_site'),
        ('site_location_flat',    'vw_archaeological_site_site_location'),
        ('bc_property_address_flat', 'vw_archaeological_site_bc_property_address')
    LOOP
        FOR r IN
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'archaeological_site'
              AND table_name   = src
              AND data_type    = 'text'
            ORDER BY ordinal_position
        LOOP
            EXECUTE format(
                $q$SELECT max(length(%I)) FROM archaeological_site.%I$q$,
                r.column_name, src
            ) INTO v_max;
            IF v_max IS NOT NULL AND v_max > 4000 THEN
                RAISE WARNING
                    'archaeological_site.%.% max length = % — truncated in databc.%',
                    src, r.column_name, v_max, vw;
            END IF;
        END LOOP;
        RAISE NOTICE 'Length check complete for archaeological_site.%', src;
    END LOOP;
END $$;
