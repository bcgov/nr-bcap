-- DataBC export view for the Repository resource model.
-- Source: repository.resource_flat
--
-- Rules applied for Oracle compatibility:
--   * resourceinstanceid cast to text
--   * All text columns wrapped with LEFT(col, 4000)
--   * Reference _ids columns removed (internal list-item UUIDs)
--   * physical_location_geom retained as PostGIS geometry
--     (Oracle Spatial clients can consume this directly)

CREATE SCHEMA IF NOT EXISTS databc;

CREATE OR REPLACE VIEW databc.vw_repository AS
SELECT
    resourceinstanceid::text                    AS resourceinstanceid,

    -- Repository Identifier
    LEFT(repository_name, 4000)                 AS repository_name,
    LEFT(repository_location_code, 4000)        AS repository_location_code,

    -- Alternate Identifiers
    LEFT(alternate_name, 4000)                  AS alternate_name,
    LEFT(alternate_code, 4000)                  AS alternate_code,

    -- Contact Information
    LEFT(address_line_1, 4000)                  AS address_line_1,
    LEFT(address_line_2, 4000)                  AS address_line_2,
    LEFT(city, 4000)                            AS city,
    LEFT(province, 4000)                        AS province,
    LEFT(postal_code, 4000)                     AS postal_code,
    LEFT(primary_email, 4000)                   AS primary_email,
    LEFT(address_notes, 4000)                   AS address_notes,
    LEFT(place_description, 4000)               AS place_description,

    -- Physical Location
    physical_location_geom,                                         -- geometry

    -- Repository Notes
    LEFT(note, 4000)                            AS note

FROM repository.resource_flat;

COMMENT ON VIEW databc.vw_repository IS
'DataBC export subset for the Repository resource model. '
'One row per repository. All text columns are capped at 4000 characters for '
'Oracle VARCHAR2 compatibility. physical_location_geom is the PostGIS geometry '
'extracted from the Physical Location node.';

-- ============================================================
-- Text-length validation
-- ============================================================
DO $$
DECLARE
    r     record;
    v_max bigint;
BEGIN
    FOR r IN
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'repository'
          AND table_name   = 'resource_flat'
          AND data_type    = 'text'
        ORDER BY ordinal_position
    LOOP
        EXECUTE format(
            $q$SELECT max(length(%I)) FROM repository.resource_flat$q$,
            r.column_name
        ) INTO v_max;
        IF v_max IS NOT NULL AND v_max > 4000 THEN
            RAISE WARNING
                'repository.resource_flat.% max length = % — truncated in databc.vw_repository',
                r.column_name, v_max;
        END IF;
    END LOOP;
    RAISE NOTICE 'Length check complete for repository.resource_flat';
END $$;
