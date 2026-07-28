-- DataBC export view for the Publication resource model.
-- Source: publication.resource_flat
--
-- Rules applied for Oracle compatibility:
--   * resourceinstanceid cast to text
--   * All text columns wrapped with LEFT(col, 4000)
--   * Reference/concept _ids columns removed (internal list-item UUIDs)
--   * File _ids columns removed (not resource links)
--   * resource-instance and resource-instance-list _id/_ids retained as join keys

CREATE SCHEMA IF NOT EXISTS databc;

CREATE OR REPLACE VIEW databc.vw_publication AS
SELECT
    resourceinstanceid::text                        AS resourceinstanceid,

    -- Reference Link (cross-resource join keys)
    LEFT(archaeological_sites, 4000)                AS archaeological_sites,
    LEFT(archaeological_sites_ids, 4000)            AS archaeological_sites_ids,  -- resource-instance-list
    LEFT(site_visits, 4000)                         AS site_visits,
    LEFT(site_visits_ids, 4000)                     AS site_visits_ids,            -- resource-instance-list
    LEFT(repositories, 4000)                        AS repositories,
    LEFT(repositories_ids, 4000)                    AS repositories_ids,           -- resource-instance-list

    -- Authors
    LEFT(other_authors_unlisted, 4000)              AS other_authors_unlisted,
    LEFT(authors, 4000)                             AS authors,
    LEFT(authors_ids, 4000)                         AS authors_ids,                -- resource-instance-list

    -- Copyright Type
    distribution_permitted,                                                         -- boolean
    LEFT(signed_agreement, 4000)                    AS signed_agreement,
    LEFT(agreement_text, 4000)                      AS agreement_text,
    LEFT(copyright_type, 4000)                      AS copyright_type,

    -- Information Carrier
    LEFT(information_carrier, 4000)                 AS information_carrier,

    -- Keyword
    LEFT(keyword, 4000)                             AS keyword,

    -- Publication Details
    LEFT(title, 4000)                               AS title,
    LEFT(other_journal_or_volume_name, 4000)        AS other_journal_or_volume_name,
    page_range_start,                                                               -- numeric
    page_range_end,                                                                 -- numeric
    LEFT(journal_or_volume_name, 4000)              AS journal_or_volume_name,
    LEFT(journal_or_volume_name_id, 4000)           AS journal_or_volume_name_id,  -- resource-instance
    LEFT(publication_type, 4000)                    AS publication_type,
    year_of_publication,                                                            -- date
    LEFT(publication_remarks, 4000)                 AS publication_remarks,

    -- Publication Identifier
    LEFT(publication_identifier_type, 4000)         AS publication_identifier_type,
    LEFT(publication_identifier, 4000)              AS publication_identifier

FROM publication.resource_flat;

COMMENT ON VIEW databc.vw_publication IS
'DataBC export subset for the Publication resource model. '
'One row per publication. All text columns are capped at 4000 characters for '
'Oracle VARCHAR2 compatibility. _ids columns link to resource instances.';

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
        WHERE table_schema = 'publication'
          AND table_name   = 'resource_flat'
          AND data_type    = 'text'
        ORDER BY ordinal_position
    LOOP
        EXECUTE format(
            $q$SELECT max(length(%I)) FROM publication.resource_flat$q$,
            r.column_name
        ) INTO v_max;
        IF v_max IS NOT NULL AND v_max > 4000 THEN
            RAISE WARNING
                'publication.resource_flat.% max length = % — truncated in databc.vw_publication',
                r.column_name, v_max;
        END IF;
    END LOOP;
    RAISE NOTICE 'Length check complete for publication.resource_flat';
END $$;
