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
-- archaeological_data  (cardinality 1)  children: cultural_material, stratigraphy, archaeological_feature, chronology, archaeological_culture, site_disturbance, additional_site_typology
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_archaeological_data CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_archaeological_data AS
WITH cultural_material AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'cultural_material_type', arches_util.reference_flat(t.tiledata -> '4abf8e50-1402-11f0-acd5-0242ac170007'),
            'cultural_material_status', arches_util.reference_flat(t.tiledata -> '5d4e5254-1402-11f0-acd5-0242ac170007'),
            'cultural_material_details', arches_util.i18n_text(t.tiledata -> 'b029a3c0-1402-11f0-a830-0242ac170007'),
            'number_of_artifacts', NULLIF(t.tiledata ->> '2423be32-1403-11f0-ae97-0242ac170007', '')::numeric,
            'repository', arches_util.resource_id(t.tiledata -> '3787b9de-5cd2-11f0-b2ee-0242ac170007')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '22508fc8-1402-11f0-acd5-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
stratigraphy AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'stratigraphy', arches_util.i18n_text(t.tiledata -> '720dd6dc-1408-11f0-9e93-0242ac170007')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '720dd6dc-1408-11f0-9e93-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
archaeological_feature AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'archaeological_feature', arches_util.reference_flat(t.tiledata -> 'a0c7cc6e-1401-11f0-acd5-0242ac170007'),
            'feature_count', NULLIF(t.tiledata ->> 'a0c7d01a-1401-11f0-acd5-0242ac170007', '')::numeric,
            'feature_remarks', arches_util.i18n_text(t.tiledata -> 'a0c7d128-1401-11f0-acd5-0242ac170007')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'a0c7cc6e-1401-11f0-acd5-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
chronology AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'start_year', to_date(NULLIF(t.tiledata ->> 'c1f5724c-140b-11f0-898b-0242ac170007', ''), 'YYYY'),
            'start_year_qualifier', arches_util.reference_flat(t.tiledata -> 'c1f576d4-140b-11f0-898b-0242ac170007'),
            'start_year_calendar', arches_util.reference_flat(t.tiledata -> 'c1f575ee-140b-11f0-898b-0242ac170007'),
            'end_year', to_date(NULLIF(t.tiledata ->> 'c1f57418-140b-11f0-898b-0242ac170007', ''), 'YYYY'),
            'end_year_qualifier', arches_util.reference_flat(t.tiledata -> 'c1f56e78-140b-11f0-898b-0242ac170007'),
            'end_year_calendar', arches_util.reference_flat(t.tiledata -> 'c1f56f86-140b-11f0-898b-0242ac170007'),
            'determination_method', arches_util.reference_flat(t.tiledata -> 'c1f57166-140b-11f0-898b-0242ac170007'),
            'information_source', arches_util.i18n_text(t.tiledata -> 'c1f57332-140b-11f0-898b-0242ac170007'),
            'chronology_remarks', arches_util.i18n_text(t.tiledata -> 'c1f57080-140b-11f0-898b-0242ac170007')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'c1f56b08-140b-11f0-898b-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
archaeological_culture AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'archaeological_culture', arches_util.reference_flat(t.tiledata -> 'fab4ba5a-1408-11f0-9e93-0242ac170007'),
            'culture_remarks', arches_util.i18n_text(t.tiledata -> 'fab4bde8-1408-11f0-9e93-0242ac170007')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'fab4ba5a-1408-11f0-9e93-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
site_disturbance AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'disturbance_period', arches_util.reference_flat(t.tiledata -> 'fb559480-140c-11f0-b9bb-0242ac170007'),
            'disturbance_cause', arches_util.reference_flat(t.tiledata -> 'fb5595c0-140c-11f0-b9bb-0242ac170007'),
            'disturbance_remarks', arches_util.i18n_text(t.tiledata -> 'fb5596b0-140c-11f0-b9bb-0242ac170007')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'fb559106-140c-11f0-b9bb-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
additional_site_typology AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'typology_class', arches_util.reference_flat(t.tiledata -> 'd6765cc8-8dec-431b-bbb5-950567e6ed1c'),
            'typology_remark', arches_util.i18n_text(t.tiledata -> 'c98387af-e430-4317-b222-9f2191194817')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'c3738e14-a521-47c1-8b52-668847a8a51e'::uuid
    GROUP BY t.parenttileid
),
archaeological_data AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'cultural_material', COALESCE(cultural_material.arr, '[]'::jsonb),
            'stratigraphy', COALESCE(stratigraphy.arr, '[]'::jsonb),
            'archaeological_feature', COALESCE(archaeological_feature.arr, '[]'::jsonb),
            'chronology', COALESCE(chronology.arr, '[]'::jsonb),
            'archaeological_culture', COALESCE(archaeological_culture.arr, '[]'::jsonb),
            'site_disturbance', COALESCE(site_disturbance.arr, '[]'::jsonb),
            'additional_site_typology', COALESCE(additional_site_typology.arr, '[]'::jsonb)
        ) AS obj
    FROM public.tiles t
    LEFT JOIN cultural_material cultural_material ON cultural_material.parenttileid = t.tileid
    LEFT JOIN stratigraphy stratigraphy ON stratigraphy.parenttileid = t.tileid
    LEFT JOIN archaeological_feature archaeological_feature ON archaeological_feature.parenttileid = t.tileid
    LEFT JOIN chronology chronology ON chronology.parenttileid = t.tileid
    LEFT JOIN archaeological_culture archaeological_culture ON archaeological_culture.parenttileid = t.tileid
    LEFT JOIN site_disturbance site_disturbance ON site_disturbance.parenttileid = t.tileid
    LEFT JOIN additional_site_typology additional_site_typology ON additional_site_typology.parenttileid = t.tileid
    WHERE t.nodegroupid = '3648fb88-1401-11f0-acd5-0242ac170007'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS archaeological_data FROM archaeological_data;

CREATE UNIQUE INDEX mv_archaeological_data_pk ON site_visit.mv_archaeological_data (resourceinstanceid);
