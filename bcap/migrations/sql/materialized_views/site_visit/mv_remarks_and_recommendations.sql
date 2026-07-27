-- GENERATED - edit sv_spec.py and re-run generate.py. Do not hand-edit.
-- Graph 2da1c15f-1ab6-4122-9dbc-d10da693ac79
-- Requires 00_arches_util.sql (arches_util helpers) to be applied first.
--
-- Reads public.tiles DIRECTLY. The generated site_visit.* views are NOT used:
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

CREATE SCHEMA IF NOT EXISTS site_visit;

-- ---------------------------------------------------------------------
-- remarks_and_recommendations  (cardinality 1)  children: recommendation, general_remark
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_remarks_and_recommendations CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_remarks_and_recommendations AS
WITH recommendation AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'recorders_recommendation', arches_util.i18n_text(t.tiledata -> '8cf43cd4-61ab-11f0-be7c-3a7a4e6803c5'),
            'archaeology_branch_recommendation', arches_util.i18n_text(t.tiledata -> 'fadb061b-2be7-4a0b-810a-51d8cee25bf8')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '8cf43a0e-61ab-11f0-be7c-3a7a4e6803c5'::uuid
    GROUP BY t.parenttileid
),
general_remark AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'remark', arches_util.i18n_text(t.tiledata -> '9625068a-61ab-11f0-be7c-3a7a4e6803c5'),
            'remark_date', to_date(NULLIF(t.tiledata ->> '962505cc-61ab-11f0-be7c-3a7a4e6803c5', ''), 'YYYY-MM-DD'),
            'remark_source', arches_util.reference_flat(t.tiledata -> '962504dc-61ab-11f0-be7c-3a7a4e6803c5')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '9625020c-61ab-11f0-be7c-3a7a4e6803c5'::uuid
    GROUP BY t.parenttileid
),
remarks_and_recommendations AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'recommendation', COALESCE(recommendation.arr, '[]'::jsonb),
            'general_remark', COALESCE(general_remark.arr, '[]'::jsonb)
        ) AS obj
    FROM public.tiles t
    LEFT JOIN recommendation recommendation ON recommendation.parenttileid = t.tileid
    LEFT JOIN general_remark general_remark ON general_remark.parenttileid = t.tileid
    WHERE t.nodegroupid = '77789d46-61ab-11f0-be7c-3a7a4e6803c5'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS remarks_and_recommendations FROM remarks_and_recommendations;

CREATE UNIQUE INDEX mv_remarks_and_recommendations_pk ON site_visit.mv_remarks_and_recommendations (resourceinstanceid);
