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

DROP MATERIALIZED VIEW IF EXISTS publication.mv_resource_v1 CASCADE;
CREATE MATERIALIZED VIEW publication.mv_resource_v1 AS
-- resource_instances is the row DRIVER, not a source of columns. It is what
-- guarantees one row per resource INCLUDING resources with zero tiles, and it
-- carries the only graphid filter in the stack. Drop the columns, keep the join.
SELECT
    r.resourceinstanceid,
    b0.reference_link,
    COALESCE(b1.information_carrier, '[]'::jsonb) AS information_carrier,
    b2.copyright_type,
    COALESCE(b3.keyword, '[]'::jsonb) AS keyword,
    COALESCE(b4.authors, '[]'::jsonb) AS authors,
    b5.publication_details,
    jsonb_build_object(
        'resourceinstanceid', r.resourceinstanceid,
        'reference_link', b0.reference_link,
        'information_carrier', COALESCE(b1.information_carrier, '[]'::jsonb),
        'copyright_type', b2.copyright_type,
        'keyword', COALESCE(b3.keyword, '[]'::jsonb),
        'authors', COALESCE(b4.authors, '[]'::jsonb),
        'publication_details', b5.publication_details
    ) AS resource
FROM public.resource_instances r
LEFT JOIN publication.mv_reference_link b0 ON b0.resourceinstanceid = r.resourceinstanceid
LEFT JOIN publication.mv_information_carrier b1 ON b1.resourceinstanceid = r.resourceinstanceid
LEFT JOIN publication.mv_copyright_type b2 ON b2.resourceinstanceid = r.resourceinstanceid
LEFT JOIN publication.mv_keyword b3 ON b3.resourceinstanceid = r.resourceinstanceid
LEFT JOIN publication.mv_authors b4 ON b4.resourceinstanceid = r.resourceinstanceid
LEFT JOIN publication.mv_publication_details b5 ON b5.resourceinstanceid = r.resourceinstanceid
WHERE r.graphid = '3caf329f-b8f7-11e6-84a5-026d961c88e6'::uuid;

CREATE UNIQUE INDEX mv_resource_v1_pk  ON publication.mv_resource_v1 (resourceinstanceid);
CREATE INDEX mv_resource_v1_res        ON publication.mv_resource_v1 USING GIN (resource jsonb_path_ops);
