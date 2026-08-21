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
-- identification  (cardinality 1)  children: temporary_number, new_site_names
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_identification CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_identification AS
WITH temporary_number AS (
    SELECT DISTINCT ON (t.parenttileid) t.parenttileid AS parenttileid,
           jsonb_build_object(
            'temporary_number', arches_util.i18n_text(t.tiledata -> 'ab674670-140d-11f0-b9bb-0242ac170007'),
            'temporary_number_assigned_by', arches_util.resource_id(t.tiledata -> 'c85b4e24-140e-11f0-8419-0242ac170007'),
            'temporary_number_assigned_date', to_date(NULLIF(t.tiledata ->> 'e3dd076e-140e-11f0-8419-0242ac170007', ''), 'YYYY-MM-DD')
        ) AS obj
    FROM public.tiles t
    WHERE t.nodegroupid = 'ab674670-140d-11f0-b9bb-0242ac170007'::uuid
    ORDER BY t.parenttileid, COALESCE(t.sortorder, 2147483647), t.tileid
),
new_site_names AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'name', arches_util.i18n_text(t.tiledata -> '6d90619c-140d-11f0-b9bb-0242ac170007'),
            'assigned_or_reported_by', arches_util.resource_id(t.tiledata -> '6d9063d6-140d-11f0-b9bb-0242ac170007'),
            'name_type', arches_util.reference_flat(t.tiledata -> '6d9065d4-140d-11f0-b9bb-0242ac170007'),
            'name_remarks', arches_util.i18n_text(t.tiledata -> '6d9066ce-140d-11f0-b9bb-0242ac170007'),
            'assigned_or_reported_date', to_date(NULLIF(t.tiledata ->> '6d9067be-140d-11f0-b9bb-0242ac170007', ''), 'YYYY-MM-DD')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '6d905dbe-140d-11f0-b9bb-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
identification AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'temporary_number', temporary_number.obj,
            'new_site_names', COALESCE(new_site_names.arr, '[]'::jsonb)
        ) AS obj
    FROM public.tiles t
    LEFT JOIN temporary_number temporary_number ON temporary_number.parenttileid = t.tileid
    LEFT JOIN new_site_names new_site_names ON new_site_names.parenttileid = t.tileid
    WHERE t.nodegroupid = '37bdda22-140d-11f0-b9bb-0242ac170007'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS identification FROM identification;

CREATE UNIQUE INDEX mv_identification_pk ON site_visit.mv_identification (resourceinstanceid);
