-- DataBC export view for the HCA Permit resource model.
-- Source: hca_permit.resource_flat
--
-- Rules applied for Oracle compatibility:
--   * resourceinstanceid cast to text (Oracle has no UUID type)
--   * All text columns wrapped with LEFT(col, 4000) (Oracle VARCHAR2 limit)
--   * Reference/concept _ids columns removed (internal list-item UUIDs)
--   * File _ids columns removed (not resource links)
--   * resource-instance and resource-instance-list _id/_ids retained as join keys

CREATE SCHEMA IF NOT EXISTS databc;

CREATE OR REPLACE VIEW databc.vw_hca_permit AS
SELECT
    resourceinstanceid::text                    AS resourceinstanceid,

    -- Permit Identification
    LEFT(permit_number, 4000)                   AS permit_number,
    LEFT(issuing_agency, 4000)                  AS issuing_agency,
    LEFT(hca_permit_type, 4000)                 AS hca_permit_type,
    LEFT(permit_holder, 4000)                   AS permit_holder,
    LEFT(permit_holder_ids, 4000)               AS permit_holder_ids    -- resource-instance-list

FROM hca_permit.resource_flat;

COMMENT ON VIEW databc.vw_hca_permit IS
'DataBC export subset for the HCA Permit resource model. '
'One row per permit. All text columns are capped at 4000 characters for '
'Oracle VARCHAR2 compatibility. _ids columns link to resource instances.';

-- ============================================================
-- Text-length validation (Oracle VARCHAR2 4000-byte limit).
-- Checks the SOURCE flat view for any text column that exceeds 4000
-- characters; those values will be silently truncated in this view.
-- This block runs at migration time; re-run manually after a full refresh.
-- ============================================================
DO $$
DECLARE
    r     record;
    v_max bigint;
BEGIN
    FOR r IN
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'hca_permit'
          AND table_name   = 'resource_flat'
          AND data_type    = 'text'
        ORDER BY ordinal_position
    LOOP
        EXECUTE format(
            $q$SELECT max(length(%I)) FROM hca_permit.resource_flat$q$,
            r.column_name
        ) INTO v_max;
        IF v_max IS NOT NULL AND v_max > 4000 THEN
            RAISE WARNING
                'hca_permit.resource_flat.% max length = % — truncated in databc.vw_hca_permit',
                r.column_name, v_max;
        END IF;
    END LOOP;
    RAISE NOTICE 'Length check complete for hca_permit.resource_flat';
END $$;
