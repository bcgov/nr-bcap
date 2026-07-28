-- GENERATED - edit rep_spec.py and re-run generate.py. Do not hand-edit.
-- Graph 3e6a2880-14d4-11ec-9df0-5254008afee6
-- Requires 00_arches_util.sql (arches_util helpers) to be applied first.
--
-- Reads public.tiles DIRECTLY. The generated repository.* views are NOT used:
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

CREATE SCHEMA IF NOT EXISTS repository;

-- ---------------------------------------------------------------------
-- repository_identifier  (cardinality 1)  children: alternate_identifiers
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS repository.mv_repository_identifier CASCADE;
CREATE MATERIALIZED VIEW repository.mv_repository_identifier AS
WITH alternate_identifiers AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'alternate_name', arches_util.i18n_text(t.tiledata -> 'a1c04d76-d075-11ec-bb64-5254008afee6'),
            'alternate_code', t.tiledata ->> '9e83e43e-5cd5-11f0-b2bb-0242ac170007'
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '86bfd67c-d075-11ec-aae2-5254008afee6'::uuid
    GROUP BY t.parenttileid
),
repository_identifier AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'repository_name', arches_util.i18n_text(t.tiledata -> 'd10365ec-14e0-11ec-b5bf-5254008afee6'),
            'repository_location_code', t.tiledata ->> '5cf2771a-5cd5-11f0-b2bb-0242ac170007',
            'alternate_identifiers', COALESCE(alternate_identifiers.arr, '[]'::jsonb)
        ) AS obj
    FROM public.tiles t
    LEFT JOIN alternate_identifiers alternate_identifiers ON alternate_identifiers.parenttileid = t.tileid
    WHERE t.nodegroupid = 'ea5a7956-14d4-11ec-aa11-5254008afee6'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS repository_identifier FROM repository_identifier;

CREATE UNIQUE INDEX mv_repository_identifier_pk ON repository.mv_repository_identifier (resourceinstanceid);
