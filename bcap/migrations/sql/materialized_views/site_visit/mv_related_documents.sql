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
-- related_documents  (cardinality 1)  children: related_site_documents, publication_reference, site_images
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_related_documents CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_related_documents AS
WITH related_site_documents AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'related_site_documents', arches_util.file_list(t.tiledata -> '55f5927c-8279-4864-ba1d-2f288ca46fcf'),
            'related_document_type', arches_util.reference_flat(t.tiledata -> 'acbdadfa-2ccf-4a68-9497-56d36dbd1021'),
            'related_document_description', arches_util.i18n_text(t.tiledata -> '844ae10f-b38b-4706-8fac-8804d04ab05e')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '55f5927c-8279-4864-ba1d-2f288ca46fcf'::uuid
    GROUP BY t.parenttileid
),
publication_reference AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'publication_reference', arches_util.resource_ids(t.tiledata -> '6ac56e05-8c19-4ef3-9f3b-f5921c278e17')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '6ac56e05-8c19-4ef3-9f3b-f5921c278e17'::uuid
    GROUP BY t.parenttileid
),
site_images AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'site_images', arches_util.file_list(t.tiledata -> 'a6536975-292e-47d1-8ebe-7e83092438bd'),
            'primary_image', NULLIF(t.tiledata ->> '696b4699-bc65-4d0e-8d48-f2a211fe5e3a', '')::boolean,
            'image_type', arches_util.reference_flat(t.tiledata -> '98c6f7ee-5c7f-4287-aeed-0168e5c40773'),
            'image_view', arches_util.reference_flat(t.tiledata -> 'c0dbd7b1-9c2b-4c27-96f3-17cb5aad7d25'),
            'image_description', arches_util.i18n_text(t.tiledata -> '10d83dfd-49d8-4bf3-9977-4acbc809b7b8'),
            'image_features', arches_util.i18n_text(t.tiledata -> '9bd92cab-7995-4940-9547-073e2eb505ac'),
            'photographer', arches_util.i18n_text(t.tiledata -> 'd20d1438-701d-47e9-8f93-7a460f3bba75'),
            'copyright', arches_util.i18n_text(t.tiledata -> '7b7f1f4c-df01-4881-b9f3-495fc9a968bc'),
            'image_date', to_date(NULLIF(t.tiledata ->> '2454579e-6884-4d1d-82f3-724f62ce4d4f', ''), 'YYYY')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'a6536975-292e-47d1-8ebe-7e83092438bd'::uuid
    GROUP BY t.parenttileid
),
related_documents AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'related_site_documents', COALESCE(related_site_documents.arr, '[]'::jsonb),
            'publication_reference', COALESCE(publication_reference.arr, '[]'::jsonb),
            'site_images', COALESCE(site_images.arr, '[]'::jsonb)
        ) AS obj
    FROM public.tiles t
    LEFT JOIN related_site_documents related_site_documents ON related_site_documents.parenttileid = t.tileid
    LEFT JOIN publication_reference publication_reference ON publication_reference.parenttileid = t.tileid
    LEFT JOIN site_images site_images ON site_images.parenttileid = t.tileid
    WHERE t.nodegroupid = '44713ace-babc-4ebe-b2f6-084ed0060f2c'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS related_documents FROM related_documents;

CREATE UNIQUE INDEX mv_related_documents_pk ON site_visit.mv_related_documents (resourceinstanceid);
