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
-- site_visit_details  (cardinality 1)  children: site_visit_team
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_site_visit_details CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_site_visit_details AS
WITH team_member AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'was_on_site', NULLIF(t.tiledata ->> '0484d428-1410-11f0-8419-0242ac170007', '')::boolean,
            'team_member', arches_util.resource_id(t.tiledata -> '0484d572-1410-11f0-8419-0242ac170007'),
            'member_roles', arches_util.reference_flat(t.tiledata -> '0484d69e-1410-11f0-8419-0242ac170007')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '0484d572-1410-11f0-8419-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
site_visit_team AS (
    SELECT DISTINCT ON (t.parenttileid) t.parenttileid AS parenttileid,
           jsonb_build_object(
            'team_member', COALESCE(team_member.arr, '[]'::jsonb)
        ) AS obj
    FROM public.tiles t
    LEFT JOIN team_member team_member ON team_member.parenttileid = t.tileid
    WHERE t.nodegroupid = '0484d0b8-1410-11f0-8419-0242ac170007'::uuid
    ORDER BY t.parenttileid, COALESCE(t.sortorder, 2147483647), t.tileid
),
site_visit_details AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'site_form_authors', arches_util.resource_ids(t.tiledata -> '4fb2db52-1410-11f0-8419-0242ac170007'),
            'site_visit_type', arches_util.reference_flat(t.tiledata -> 'e39372c4-df58-11ef-8fa3-0242ac170009'),
            'is_site_visit_permitted', NULLIF(t.tiledata ->> 'fb01d6a1-cac8-4b16-8f2c-5472213aeec6', '')::boolean,
            'first_date_of_site_visit', to_date(NULLIF(t.tiledata ->> '745b0462-140f-11f0-8419-0242ac170007', ''), 'YYYY-MM-DD'),
            'last_date_of_site_visit', to_date(NULLIF(t.tiledata ->> '1de04042-df59-11ef-8fa3-0242ac170009', ''), 'YYYY-MM-DD'),
            'project_description', arches_util.i18n_text(t.tiledata -> 'fbfbb0a6-df58-11ef-8fa3-0242ac170009'),
            'associated_permit', arches_util.resource_ids(t.tiledata -> 'b03790fe-df58-11ef-8fa3-0242ac170009'),
            'archaeological_site', arches_util.resource_id(t.tiledata -> 'cd722a58-df58-11ef-8fa3-0242ac170009'),
            'affiliation', arches_util.resource_id(t.tiledata -> '69273f50-4c9c-11f0-9f73-0242ac170007'),
            'site_visit_team', site_visit_team.obj
        ) AS obj
    FROM public.tiles t
    LEFT JOIN site_visit_team site_visit_team ON site_visit_team.parenttileid = t.tileid
    WHERE t.nodegroupid = '887edb3a-df58-11ef-8fa3-0242ac170009'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS site_visit_details FROM site_visit_details;

CREATE UNIQUE INDEX mv_site_visit_details_pk ON site_visit.mv_site_visit_details (resourceinstanceid);
