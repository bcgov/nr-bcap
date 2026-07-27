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
-- contact_information  (cardinality 1)  children: physical_location
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS repository.mv_contact_information CASCADE;
CREATE MATERIALIZED VIEW repository.mv_contact_information AS
WITH geom_physical_location AS (
    SELECT gg.tileid, ST_Collect(ST_Transform(gg.geom, 4326)) AS geom
    FROM public.geojson_geometries gg
    WHERE gg.nodeid = 'ba9252e2-14d5-11ec-a57a-5254008afee6'::uuid
    GROUP BY gg.tileid
),
physical_location AS (
    SELECT DISTINCT ON (t.parenttileid) t.parenttileid AS parenttileid,
           jsonb_build_object(
            'physical_location', CASE WHEN g.geom IS NULL THEN NULL ELSE ST_AsGeoJSON(g.geom, 7)::jsonb END
        ) AS obj
    FROM public.tiles t
    LEFT JOIN geom_physical_location g ON g.tileid = t.tileid
    WHERE t.nodegroupid = 'ba9252e2-14d5-11ec-a57a-5254008afee6'::uuid
    ORDER BY t.parenttileid, COALESCE(t.sortorder, 2147483647), t.tileid
),
contact_information AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'city', arches_util.i18n_text(t.tiledata -> '2e2e41aa-0b03-11ee-ae56-5254004d77d3'),
            'province', arches_util.reference_flat(t.tiledata -> '2e2e47e0-0b03-11ee-ae56-5254004d77d3'),
            'address_line_1', arches_util.i18n_text(t.tiledata -> '2e2e4a74-0b03-11ee-ae56-5254004d77d3'),
            'address_line_2', arches_util.i18n_text(t.tiledata -> '2e2e51cc-0b03-11ee-ae56-5254004d77d3'),
            'postal_code', arches_util.i18n_text(t.tiledata -> '2e2e5488-0b03-11ee-ae56-5254004d77d3'),
            'address_notes', arches_util.i18n_text(t.tiledata -> '2e2e567c-0b03-11ee-ae56-5254004d77d3'),
            'primary_email', arches_util.i18n_text(t.tiledata -> '5c894e04-0aff-11ee-87c8-0050568377a0'),
            'place_description', arches_util.i18n_text(t.tiledata -> 'ba927d08-14d5-11ec-a57a-5254008afee6'),
            'physical_location', physical_location.obj
        ) AS obj
    FROM public.tiles t
    LEFT JOIN physical_location physical_location ON physical_location.parenttileid = t.tileid
    WHERE t.nodegroupid = 'ba927470-14d5-11ec-a57a-5254008afee6'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS contact_information FROM contact_information;

CREATE UNIQUE INDEX mv_contact_information_pk ON repository.mv_contact_information (resourceinstanceid);
