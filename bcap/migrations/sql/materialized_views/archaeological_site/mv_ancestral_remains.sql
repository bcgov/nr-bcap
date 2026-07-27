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
-- ancestral_remains  (cardinality 1)  children: restricted_ancestral_remains_remark
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_ancestral_remains CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_ancestral_remains AS
WITH restricted_ancestral_remains_remark AS (
    SELECT DISTINCT ON (t.parenttileid) t.parenttileid AS parenttileid,
           jsonb_build_object(
            'restricted_ancestral_remains_remark', arches_util.i18n_text(t.tiledata -> '1417996e-64ad-11f0-a4ef-6e5bb479055b'),
            'remains_remark_made_by', arches_util.resource_id(t.tiledata -> '14179edc-64ad-11f0-a4ef-6e5bb479055b'),
            'remains_remark_entry_date', to_date(NULLIF(t.tiledata ->> '1417a09e-64ad-11f0-a4ef-6e5bb479055b', ''), 'YYYY-MM-DD')
        ) AS obj
    FROM public.tiles t
    WHERE t.nodegroupid = '1417996e-64ad-11f0-a4ef-6e5bb479055b'::uuid
    ORDER BY t.parenttileid, COALESCE(t.sortorder, 2147483647), t.tileid
),
ancestral_remains AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'restricted_ancestral_remains_remark', restricted_ancestral_remains_remark.obj
        ) AS obj
    FROM public.tiles t
    LEFT JOIN restricted_ancestral_remains_remark restricted_ancestral_remains_remark ON restricted_ancestral_remains_remark.parenttileid = t.tileid
    WHERE t.nodegroupid = '14179ca2-64ad-11f0-a4ef-6e5bb479055b'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS ancestral_remains FROM ancestral_remains;

CREATE UNIQUE INDEX mv_ancestral_remains_pk ON archaeological_site.mv_ancestral_remains (resourceinstanceid);
