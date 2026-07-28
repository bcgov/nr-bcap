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
-- related_documents  (cardinality 1)  children: related_site_documents, publication_reference, site_images
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_related_documents CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_related_documents AS
WITH related_site_documents AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'related_site_documents', arches_util.file_list(t.tiledata -> '2ad161ee-50ad-11f0-a6c8-0242ac170006'),
            'related_document_type', arches_util.reference_flat(t.tiledata -> '2ad16676-50ad-11f0-a6c8-0242ac170006'),
            'related_document_description', arches_util.i18n_text(t.tiledata -> '2ad1655e-50ad-11f0-a6c8-0242ac170006')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '2ad161ee-50ad-11f0-a6c8-0242ac170006'::uuid
    GROUP BY t.parenttileid
),
publication_reference AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'publication_reference', arches_util.resource_ids(t.tiledata -> 'bb157a2a-01d8-11f0-850c-0242ac170007')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'bb157a2a-01d8-11f0-850c-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
site_images AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'site_images', arches_util.file_list(t.tiledata -> 'c81626e8-01d8-11f0-850c-0242ac170007'),
            'primary_image', NULLIF(t.tiledata ->> 'c8163160-01d8-11f0-850c-0242ac170007', '')::boolean,
            'image_type', arches_util.reference_flat(t.tiledata -> 'c8162ad0-01d8-11f0-850c-0242ac170007'),
            'image_view', arches_util.reference_flat(t.tiledata -> 'c8162d0a-01d8-11f0-850c-0242ac170007'),
            'image_description', arches_util.i18n_text(t.tiledata -> 'c8162df0-01d8-11f0-850c-0242ac170007'),
            'image_features', arches_util.i18n_text(t.tiledata -> 'c816308e-01d8-11f0-850c-0242ac170007'),
            'photographer', arches_util.i18n_text(t.tiledata -> 'c8162c2e-01d8-11f0-850c-0242ac170007'),
            'copyright', arches_util.i18n_text(t.tiledata -> 'c8162ecc-01d8-11f0-850c-0242ac170007'),
            'image_date', to_date(NULLIF(t.tiledata ->> 'c8162fa8-01d8-11f0-850c-0242ac170007', ''), 'YYYY')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'c81626e8-01d8-11f0-850c-0242ac170007'::uuid
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
    WHERE t.nodegroupid = '347e24f8-01d8-11f0-850c-0242ac170007'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS related_documents FROM related_documents;

CREATE UNIQUE INDEX mv_related_documents_pk ON archaeological_site.mv_related_documents (resourceinstanceid);
