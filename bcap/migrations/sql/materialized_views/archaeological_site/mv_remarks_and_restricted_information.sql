-- GENERATED - edit as_spec.py and re-run generate.py. Do not hand-edit.
-- Graph cef9c510-e3e6-4057-ac08-89ad926180b4
-- Requires 00_arches_util.sql (arches_util helpers) to be applied first.
--
-- Reads public.tiles DIRECTLY. The generated archaeological_site.* views are NOT used:
-- each LEFT JOINs edit_log twice with a text->uuid cast that no index can serve.
--
-- INVARIANTS (downstream depends on these - do not change silently):
--   * every key ALWAYS present; empty means null, never absent. No jsonb_strip_nulls.
--   * cardinality-n children are ALWAYS a jsonb array, [] when empty, never null.
--   * cardinality-1 branches are an object, or null when the tile does not exist.
--   * array order is tiles.sortorder, then tileid. Stable across refreshes.

SET client_min_messages = warning;   -- ST_MakeValid emits a NOTICE per repair
SET maintenance_work_mem = '512MB';
SET work_mem             = '128MB';

CREATE SCHEMA IF NOT EXISTS archaeological_site;

-- ---------------------------------------------------------------------
-- remarks_and_restricted_information  (cardinality 1)  children: remark_keyword, restricted_document, hca_contravention, contravention_document, restricted_information, general_remark_information, conviction
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_remarks_and_restricted_information CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_remarks_and_restricted_information AS
WITH remark_keyword AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'remark_keyword', arches_util.i18n_text(t.tiledata -> 'dc827931-05ed-43e4-8da6-e99c0d02dae7')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'dc827931-05ed-43e4-8da6-e99c0d02dae7'::uuid
    GROUP BY t.parenttileid
),
restricted_document AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'restricted_document', arches_util.file_list(t.tiledata -> '250ed6fe-61a8-11f0-ad02-3a7a4e6803c5')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '250ed6fe-61a8-11f0-ad02-3a7a4e6803c5'::uuid
    GROUP BY t.parenttileid
),
hca_contravention AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'inventory_remark', arches_util.i18n_text(t.tiledata -> '41fb5e20-61a5-11f0-9674-3a7a4e6803c5'),
            'contravention_address', arches_util.i18n_text(t.tiledata -> '41fb5eca-61a5-11f0-9674-3a7a4e6803c5'),
            'contravention_pid', arches_util.i18n_text(t.tiledata -> '41fb5f7e-61a5-11f0-9674-3a7a4e6803c5'),
            'nros_file_number', arches_util.i18n_text(t.tiledata -> '41fb603c-61a5-11f0-9674-3a7a4e6803c5')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '41fb5948-61a5-11f0-9674-3a7a4e6803c5'::uuid
    GROUP BY t.parenttileid
),
contravention_document AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'contravention_document', arches_util.file_list(t.tiledata -> '1bebc404-61a5-11f0-9674-3a7a4e6803c5')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '1bebc404-61a5-11f0-9674-3a7a4e6803c5'::uuid
    GROUP BY t.parenttileid
),
restricted_information AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'restricted_entry_date', to_date(NULLIF(t.tiledata ->> 'b0ed34b2-61a4-11f0-9674-3a7a4e6803c5', ''), 'YYYY-MM-DD'),
            'restricted_person', arches_util.resource_id(t.tiledata -> 'b0ed35ac-61a4-11f0-9674-3a7a4e6803c5'),
            'restricted_remark', arches_util.i18n_text(t.tiledata -> 'b0ed366a-61a4-11f0-9674-3a7a4e6803c5')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'b0ed31c4-61a4-11f0-9674-3a7a4e6803c5'::uuid
    GROUP BY t.parenttileid
),
general_remark_information AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'general_remark_source', arches_util.reference_flat(t.tiledata -> '05baef2a-61a5-11f0-9674-3a7a4e6803c5'),
            'general_remark_date', to_date(NULLIF(t.tiledata ->> '05baf01a-61a5-11f0-9674-3a7a4e6803c5', ''), 'YYYY-MM-DD'),
            'general_remark', arches_util.i18n_text(t.tiledata -> '05baf0e2-61a5-11f0-9674-3a7a4e6803c5')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '05baebf6-61a5-11f0-9674-3a7a4e6803c5'::uuid
    GROUP BY t.parenttileid
),
conviction AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'conviction_date', to_date(NULLIF(t.tiledata ->> 'c515a532-619f-11f0-acf4-3a7a4e6803c5', ''), 'YYYY-MM-DD'),
            'conviction_details', arches_util.i18n_text(t.tiledata -> 'c515a668-619f-11f0-acf4-3a7a4e6803c5')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'c5159e8e-619f-11f0-acf4-3a7a4e6803c5'::uuid
    GROUP BY t.parenttileid
),
remarks_and_restricted_information AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'remark_keyword', COALESCE(remark_keyword.arr, '[]'::jsonb),
            'restricted_document', COALESCE(restricted_document.arr, '[]'::jsonb),
            'hca_contravention', COALESCE(hca_contravention.arr, '[]'::jsonb),
            'contravention_document', COALESCE(contravention_document.arr, '[]'::jsonb),
            'restricted_information', COALESCE(restricted_information.arr, '[]'::jsonb),
            'general_remark_information', COALESCE(general_remark_information.arr, '[]'::jsonb),
            'conviction', COALESCE(conviction.arr, '[]'::jsonb)
        ) AS obj
    FROM public.tiles t
    LEFT JOIN remark_keyword remark_keyword ON remark_keyword.parenttileid = t.tileid
    LEFT JOIN restricted_document restricted_document ON restricted_document.parenttileid = t.tileid
    LEFT JOIN hca_contravention hca_contravention ON hca_contravention.parenttileid = t.tileid
    LEFT JOIN contravention_document contravention_document ON contravention_document.parenttileid = t.tileid
    LEFT JOIN restricted_information restricted_information ON restricted_information.parenttileid = t.tileid
    LEFT JOIN general_remark_information general_remark_information ON general_remark_information.parenttileid = t.tileid
    LEFT JOIN conviction conviction ON conviction.parenttileid = t.tileid
    WHERE t.nodegroupid = '75c91464-619f-11f0-acf4-3a7a4e6803c5'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS remarks_and_restricted_information FROM remarks_and_restricted_information;

CREATE UNIQUE INDEX mv_remarks_and_restricted_information_pk ON archaeological_site.mv_remarks_and_restricted_information (resourceinstanceid);
