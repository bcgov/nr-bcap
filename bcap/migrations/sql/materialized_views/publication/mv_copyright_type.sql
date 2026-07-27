-- GENERATED - edit pub_spec.py and re-run generate.py. Do not hand-edit.
-- Graph 3caf329f-b8f7-11e6-84a5-026d961c88e6
-- Requires 00_arches_util.sql (arches_util helpers) to be applied first.
--
-- Reads public.tiles DIRECTLY. The generated publication.* views are NOT used:
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

CREATE SCHEMA IF NOT EXISTS publication;

-- ---------------------------------------------------------------------
-- copyright_type  (cardinality 1)
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS publication.mv_copyright_type CASCADE;
CREATE MATERIALIZED VIEW publication.mv_copyright_type AS
WITH copyright_type AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'distribution_permitted', NULLIF(t.tiledata ->> 'a5f5cc8c-c40c-11ed-82cd-5254004d77d3', '')::boolean,
            'signed_agreement', arches_util.file_list(t.tiledata -> 'a5f5d268-c40c-11ed-82cd-5254004d77d3'),
            'agreement_text', arches_util.i18n_text(t.tiledata -> 'a5f5d6fa-c40c-11ed-82cd-5254004d77d3'),
            'copyright_type', arches_util.reference_flat(t.tiledata -> 'a5f5c7b4-c40c-11ed-82cd-5254004d77d3')
        ) AS obj
    FROM public.tiles t
    WHERE t.nodegroupid = 'a5f5c7b4-c40c-11ed-82cd-5254004d77d3'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS copyright_type FROM copyright_type;

CREATE UNIQUE INDEX mv_copyright_type_pk ON publication.mv_copyright_type (resourceinstanceid);
