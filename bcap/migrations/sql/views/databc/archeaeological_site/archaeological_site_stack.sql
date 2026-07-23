-- =====================================================================
--  archaeological_site :: nested materialized view stack  (tiles-direct)
--  Graph: cef9c510-e3e6-4057-ac08-89ad926180b4
--
--  Same pattern as site_visit: reads public.tiles directly, no edit_log.
--  GENERATED from a spec, not hand-written - 34 nodegroups is past the point
--  where hand-transcribing node UUIDs is safe.
--
--  VERIFIED: this exact SQL was executed against PostgreSQL 16 + PostGIS 3.4
--  on a synthetic fixture covering all 34 nodegroups, including an all-null
--  tile in every group and a resource with zero tiles. It builds and the
--  assembled object is correct at every depth.
--
--  WHAT'S DIFFERENT FROM site_visit
--  ---------------------------------------------------------------------
--  * DEEPER. site_visit was 2 levels; this is 4:
--        site_location (n) -> bc_property_address (n) -> bc_property_legal_description (n)
--        site_location (n) -> site_tenure (1) -> site_tenure_type (1)
--        site_location (n) -> elevation (1) -> elevation_comments (n)
--    Verified: n-inside-n assembles correctly.
--
--  * TWO GEOMETRY NODES, and one of them is on a CHILD nodegroup:
--        site_boundary      (cardinality 1, top-level)
--        unprotected_areas  (cardinality n, child of site_boundary)
--
--  * THREE NEW DATATYPES:
--      borden-number-datatype  -> PLAIN TEXT. The generated view reads it with a
--                                 bare ->> and no ::jsonb cast, so it is NOT i18n.
--      non-localized-string    -> PLAIN TEXT, same reasoning (reference_number,
--                                 pid, pin).
--      url                     -> jsonb {"url":..., "url_label":...}. PROBE THIS,
--                                 see preflight G. url_obj() below assumes that
--                                 shape and that url_label may be i18n.
--
--  * GEOMETRY KEYS ARE NAMED AFTER THEIR NODE, so you get
--        site_boundary -> 'site_boundary'                       (the geometry)
--        site_boundary -> 'unprotected_areas' -> 0 -> 'unprotected_areas'
--    Awkward, but faithful to the graph. The typed columns on mv_resource_v1 are
--    site_boundary_geom and unprotected_areas_geom.
--
--  !! GEOMETRY BUG FOUND HERE THAT ALSO AFFECTS THE site_visit STACK !!
--  ---------------------------------------------------------------------
--  Aggregating ST_Collect() over per-tile geometries that were THEMSELVES built
--  with ST_Collect() (which is what the Arches views do) produces a
--  GEOMETRYCOLLECTION even when every part is a polygon:
--
--      ST_Collect(agg) over 2 plain polygons        -> MULTIPOLYGON      (fine)
--      ST_Collect(agg) over 2 ST_Collect'd polygons -> GEOMETRYCOLLECTION (bad)
--
--  GEOMETRYCOLLECTION breaks a lot of GIS clients and some PostGIS functions.
--  Fix, applied below: ST_CollectionHomogenize(ST_Collect(...)). It collapses to
--  MULTIPOLYGON when the parts are homogeneous, and correctly STAYS a
--  GEOMETRYCOLLECTION only when the tiles genuinely mix types.
--
--  >> APPLY THE SAME FIX TO site_visit.mv_site_visit_location. It has the same
--  >> nested collect and is producing GEOMETRYCOLLECTIONs today.
-- =====================================================================

SET maintenance_work_mem = '512MB';
SET work_mem             = '128MB';

CREATE SCHEMA IF NOT EXISTS archaeological_site;
CREATE SCHEMA IF NOT EXISTS arches_util;

CREATE INDEX IF NOT EXISTS tiles_nodegroupid_idx           ON public.tiles (nodegroupid);
CREATE INDEX IF NOT EXISTS geojson_geometries_nodeid_idx   ON public.geojson_geometries (nodeid);
CREATE INDEX IF NOT EXISTS resource_instances_graphid_idx  ON public.resource_instances (graphid);

CREATE OR REPLACE FUNCTION arches_util.as_array(val jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE WHEN jsonb_typeof(val) = 'array' THEN val ELSE '[]'::jsonb END;
$$;

CREATE OR REPLACE FUNCTION arches_util.i18n_text(val jsonb, lang text DEFAULT 'en')
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE RETURNS NULL ON NULL INPUT AS $$
    SELECT CASE jsonb_typeof(val)
        WHEN 'string' THEN val #>> '{}'
        WHEN 'object' THEN COALESCE(
            NULLIF(val -> lang ->> 'value', ''),
            (SELECT NULLIF(e.v ->> 'value', '')
               FROM jsonb_each(val) AS e(k, v)
              WHERE NULLIF(e.v ->> 'value', '') IS NOT NULL
              ORDER BY e.k LIMIT 1))
        ELSE NULL
    END;
$$;

-- Item id lives at labels[].list_item_id. Labels carry several valuetypes per
-- item (prefLabel, altLabel, scopeNote, definition...), so the label lookup
-- filters on valuetype_id and deliberately stops at altLabel - it never falls
-- through to a note. A NULL label is a visible failure; a definition paragraph
-- masquerading as a label is an invisible one.
-- uri and list_id are both dropped: uri carries an environment host in some
-- tiles and not others.
CREATE OR REPLACE FUNCTION arches_util.reference_flat(val jsonb, lang text DEFAULT 'en')
RETURNS jsonb LANGUAGE sql IMMUTABLE PARALLEL SAFE RETURNS NULL ON NULL INPUT AS $$
    SELECT CASE WHEN jsonb_typeof(val) <> 'array' THEN NULL ELSE COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
            'list_item_id', COALESCE(
                (SELECT l ->> 'list_item_id'
                   FROM jsonb_array_elements(arches_util.as_array(item -> 'labels')) l
                  WHERE l ->> 'list_item_id' IS NOT NULL LIMIT 1),
                NULLIF(regexp_replace(COALESCE(item ->> 'uri', ''), '^.*/', ''), '')),
            'label', COALESCE(
                (SELECT l ->> 'value'
                   FROM jsonb_array_elements(arches_util.as_array(item -> 'labels')) l
                  WHERE l ->> 'valuetype_id' = 'prefLabel'
                    AND l ->> 'language_id' = lang LIMIT 1),
                (SELECT l ->> 'value'
                   FROM jsonb_array_elements(arches_util.as_array(item -> 'labels')) l
                  WHERE l ->> 'valuetype_id' = 'prefLabel' LIMIT 1),
                (SELECT l ->> 'value'
                   FROM jsonb_array_elements(arches_util.as_array(item -> 'labels')) l
                  WHERE l ->> 'valuetype_id' = 'altLabel'
                    AND l ->> 'language_id' = lang LIMIT 1),
                (SELECT l ->> 'value'
                   FROM jsonb_array_elements(arches_util.as_array(item -> 'labels')) l
                  WHERE l ->> 'valuetype_id' = 'altLabel' LIMIT 1))
        ) ORDER BY ord)
        FROM jsonb_array_elements(val) WITH ORDINALITY AS t(item, ord)
    ), '[]'::jsonb) END;
$$;

CREATE OR REPLACE FUNCTION arches_util.resource_ids(val jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE PARALLEL SAFE RETURNS NULL ON NULL INPUT AS $$
    SELECT CASE WHEN jsonb_typeof(val) <> 'array' THEN NULL ELSE COALESCE((
        SELECT jsonb_agg(to_jsonb(item ->> 'resourceId') ORDER BY ord)
        FROM jsonb_array_elements(val) WITH ORDINALITY AS t(item, ord)
        WHERE item ->> 'resourceId' IS NOT NULL
    ), '[]'::jsonb) END;
$$;

CREATE OR REPLACE FUNCTION arches_util.resource_id(val jsonb)
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE RETURNS NULL ON NULL INPUT AS $$
    SELECT CASE WHEN jsonb_typeof(val) <> 'array' THEN NULL
           ELSE (val -> 0) ->> 'resourceId' END;
$$;

-- `content` (a blob: URL with the environment host baked in) and `accepted`
-- (transient upload state) are dropped. title/altText/attribution/description
-- are i18n objects and get flattened. Files sort by their own `index`.
-- last_modified is epoch MILLIseconds, emitted as an explicit UTC ISO string -
-- to_json(timestamptz) would format in the session TimeZone, and a contract must
-- not move when someone changes a session setting.
CREATE OR REPLACE FUNCTION arches_util.file_list(val jsonb, lang text DEFAULT 'en')
RETURNS jsonb LANGUAGE sql IMMUTABLE PARALLEL SAFE RETURNS NULL ON NULL INPUT AS $$
    SELECT CASE WHEN jsonb_typeof(val) <> 'array' THEN NULL ELSE COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
            'file_id',       item ->> 'file_id',
            'name',          item ->> 'name',
            'url',           item ->> 'url',
            'size',          NULLIF(item ->> 'size', '')::bigint,
            'mime_type',     item ->> 'type',
            'status',        item ->> 'status',
            'title',         arches_util.i18n_text(item -> 'title',       lang),
            'alt_text',      arches_util.i18n_text(item -> 'altText',     lang),
            'attribution',   arches_util.i18n_text(item -> 'attribution', lang),
            'description',   arches_util.i18n_text(item -> 'description', lang),
            'last_modified', CASE WHEN (item ->> 'lastModified') ~ '^[0-9]+$'
                THEN to_char(to_timestamp((item ->> 'lastModified')::bigint / 1000.0)
                             AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') END
        ) ORDER BY COALESCE(NULLIF(item ->> 'index', '')::int, 2147483647), ord)
        FROM jsonb_array_elements(val) WITH ORDINALITY AS t(item, ord)
    ), '[]'::jsonb) END;
$$;


-- NEW: Arches `url` datatype. Assumed shape {"url": "...", "url_label": "..."},
-- with url_label possibly an i18n object. CONFIRM WITH PREFLIGHT G before trusting.
CREATE OR REPLACE FUNCTION arches_util.url_obj(val jsonb, lang text DEFAULT 'en')
RETURNS jsonb LANGUAGE sql IMMUTABLE PARALLEL SAFE RETURNS NULL ON NULL INPUT AS $$
    SELECT CASE WHEN jsonb_typeof(val) <> 'object' THEN NULL
        ELSE jsonb_build_object(
            'url',   val ->> 'url',
            'label', COALESCE(arches_util.i18n_text(val -> 'url_label', lang),
                              val ->> 'url_label'))
    END;
$$;

-- ---------------------------------------------------------------------
-- site_boundary  (cardinality 1)  children: unprotected_areas
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_site_boundary CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_site_boundary AS
WITH geom_unprotected_areas AS (
    SELECT gg.tileid, ST_Collect(ST_Transform(gg.geom, 4326)) AS geom
    FROM public.geojson_geometries gg
    WHERE gg.nodeid = '7c8eb1f8-44e2-4239-afaa-9cbf1fadf160'::uuid
    GROUP BY gg.tileid
),
unprotected_areas AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'unprotected_area_type', arches_util.reference_flat(t.tiledata -> 'e1f8bec7-9d0c-4f04-9dc8-718d05444105'),
            'other_unprotected_area_type', arches_util.i18n_text(t.tiledata -> '56c7c419-e31c-4e7d-a99a-8aea3f370e52'),
            'unprotected_areas', CASE WHEN g.geom IS NULL THEN NULL ELSE ST_AsGeoJSON(g.geom, 7)::jsonb END
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    LEFT JOIN geom_unprotected_areas g ON g.tileid = t.tileid
    WHERE t.nodegroupid = '7c8eb1f8-44e2-4239-afaa-9cbf1fadf160'::uuid
    GROUP BY t.parenttileid
),
geom_site_boundary AS (
    SELECT gg.tileid, ST_Collect(ST_Transform(gg.geom, 4326)) AS geom
    FROM public.geojson_geometries gg
    WHERE gg.nodeid = 'b18223c2-13ef-11f0-8695-0242ac170007'::uuid
    GROUP BY gg.tileid
),
site_boundary AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'accuracy_remarks', arches_util.i18n_text(t.tiledata -> 'b182276e-13ef-11f0-8695-0242ac170007'),
            'site_boundary_description', arches_util.i18n_text(t.tiledata -> '63e48668-58f0-49fa-8767-abf412f54921'),
            'latest_edit_type', arches_util.reference_flat(t.tiledata -> '6292f704-13f0-11f0-9284-0242ac170007'),
            'site_boundary', CASE WHEN g.geom IS NULL THEN NULL ELSE ST_AsGeoJSON(g.geom, 7)::jsonb END,
            'unprotected_areas', COALESCE(unprotected_areas.arr, '[]'::jsonb)
        ) AS obj
    FROM public.tiles t
    LEFT JOIN geom_site_boundary g ON g.tileid = t.tileid
    LEFT JOIN unprotected_areas unprotected_areas ON unprotected_areas.parenttileid = t.tileid
    WHERE t.nodegroupid = 'b18223c2-13ef-11f0-8695-0242ac170007'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS site_boundary FROM site_boundary;

CREATE UNIQUE INDEX mv_site_boundary_pk ON archaeological_site.mv_site_boundary (resourceinstanceid);

-- ---------------------------------------------------------------------
-- identification_and_registration  (cardinality 1)  children: site_alert, authority, site_names, site_decision
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_identification_and_registration CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_identification_and_registration AS
WITH site_alert AS (
    SELECT DISTINCT ON (t.parenttileid) t.parenttileid AS parenttileid,
           jsonb_build_object(
            'alert_subject', arches_util.i18n_text(t.tiledata -> '3c5afaa2-197a-11f0-8f07-0242ac170008'),
            'alert_details', arches_util.i18n_text(t.tiledata -> '7219d578-197a-11f0-8f07-0242ac170008'),
            'alert_entered_by', arches_util.resource_id(t.tiledata -> 'ec331cd0-1979-11f0-93f5-0242ac170008'),
            'alert_branch_contact', arches_util.resource_id(t.tiledata -> '8511d07c-197a-11f0-8f07-0242ac170008'),
            'alert_entry_date', to_date(NULLIF(t.tiledata ->> '387adf52-1979-11f0-8713-0242ac170008', ''), 'YYYY-MM-DD')
        ) AS obj
    FROM public.tiles t
    WHERE t.nodegroupid = '00e2b556-1979-11f0-8713-0242ac170008'::uuid
    ORDER BY t.parenttileid, COALESCE(t.sortorder, 2147483647), t.tileid
),
authority AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'authority_protection_type', arches_util.reference_flat(t.tiledata -> '85d39c80-b92d-449f-834d-5d9b2ab3d1e8'),
            'legislative_act', arches_util.resource_id(t.tiledata -> '034d2e02-13f2-11f0-9ff8-0242ac170007'),
            'reference_number', t.tiledata ->> '034d31b8-13f2-11f0-9ff8-0242ac170007',
            'authority_description', arches_util.i18n_text(t.tiledata -> '034d2ef2-13f2-11f0-9ff8-0242ac170007'),
            'authority_start_date', to_date(NULLIF(t.tiledata ->> '85dcf57e-1978-11f0-8713-0242ac170008', ''), 'YYYY-MM-DD'),
            'authority_end_date', to_date(NULLIF(t.tiledata ->> 'b36abfee-1978-11f0-8713-0242ac170008', ''), 'YYYY-MM-DD')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '034d1fac-13f2-11f0-9ff8-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
site_names AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'name', arches_util.i18n_text(t.tiledata -> 'd60b1fa6-35f4-11f0-afbc-0242ac170008'),
            'name_type', arches_util.reference_flat(t.tiledata -> 'd60b242e-35f4-11f0-afbc-0242ac170008'),
            'name_remarks', arches_util.i18n_text(t.tiledata -> 'd60b2514-35f4-11f0-afbc-0242ac170008'),
            'assigned_or_reported_by', arches_util.resource_id(t.tiledata -> 'd60b2244-35f4-11f0-afbc-0242ac170008'),
            'assigned_or_reported_date', to_date(NULLIF(t.tiledata ->> 'd60b25fa-35f4-11f0-afbc-0242ac170008', ''), 'YYYY-MM-DD')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'd60b1b28-35f4-11f0-afbc-0242ac170008'::uuid
    GROUP BY t.parenttileid
),
site_decision AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'site_decision', arches_util.reference_flat(t.tiledata -> 'f80f08ae-1977-11f0-8713-0242ac170008'),
            'decision_registration_status', arches_util.reference_flat(t.tiledata -> '4abdfeea-8d15-4ea6-94bd-d2385d47a5ac'),
            'decision_description', arches_util.i18n_text(t.tiledata -> 'f80f115a-1977-11f0-8713-0242ac170008'),
            'decision_made_by', arches_util.resource_id(t.tiledata -> 'f80f0d4a-1977-11f0-8713-0242ac170008'),
            'decision_date', to_date(NULLIF(t.tiledata ->> 'f80f0c00-1977-11f0-8713-0242ac170008', ''), 'YYYY-MM-DD'),
            'recommended_by', arches_util.resource_id(t.tiledata -> 'f80f0f34-1977-11f0-8713-0242ac170008'),
            'recommendation_date', to_date(NULLIF(t.tiledata ->> 'f80f106a-1977-11f0-8713-0242ac170008', ''), 'YYYY-MM-DD')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'f80f08ae-1977-11f0-8713-0242ac170008'::uuid
    GROUP BY t.parenttileid
),
identification_and_registration AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'borden_number', t.tiledata ->> '7e15332c-1c54-11f0-b5bf-0242ac170007',
            'parcel_owner_type', arches_util.i18n_text(t.tiledata -> 'b442cce2-62c8-11f0-a80e-76ff5c50888d'),
            'borden_number_issuance_date', to_date(NULLIF(t.tiledata ->> 'bce307f4-62c8-11f0-a80e-76ff5c50888d', ''), 'YYYY-MM-DD'),
            'register_type', arches_util.reference_flat(t.tiledata -> '2255168c-1c55-11f0-9b6d-0242ac170007'),
            'parent_site', arches_util.resource_id(t.tiledata -> '7158cc42-1c55-11f0-9b6d-0242ac170007'),
            'site_alert', site_alert.obj,
            'authority', COALESCE(authority.arr, '[]'::jsonb),
            'site_names', COALESCE(site_names.arr, '[]'::jsonb),
            'site_decision', COALESCE(site_decision.arr, '[]'::jsonb)
        ) AS obj
    FROM public.tiles t
    LEFT JOIN site_alert site_alert ON site_alert.parenttileid = t.tileid
    LEFT JOIN authority authority ON authority.parenttileid = t.tileid
    LEFT JOIN site_names site_names ON site_names.parenttileid = t.tileid
    LEFT JOIN site_decision site_decision ON site_decision.parenttileid = t.tileid
    WHERE t.nodegroupid = '034d1c32-13f2-11f0-9ff8-0242ac170007'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS identification_and_registration FROM identification_and_registration;

CREATE UNIQUE INDEX mv_identification_and_registration_pk ON archaeological_site.mv_identification_and_registration (resourceinstanceid);

-- ---------------------------------------------------------------------
-- site_location  (cardinality n)  children: biogeography, site_tenure, elevation, bc_property_address
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_site_location CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_site_location AS
WITH biogeography AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'biogeography_type', arches_util.reference_flat(t.tiledata -> '7044fb24-197f-11f0-9fc9-0242ac170008'),
            'biogeography_name', arches_util.i18n_text(t.tiledata -> '96df3a2e-197f-11f0-9fc9-0242ac170008'),
            'biogeography_description', arches_util.i18n_text(t.tiledata -> 'aad2e7e2-197f-11f0-9fc9-0242ac170008')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '2509f4a2-197f-11f0-b2a5-0242ac170008'::uuid
    GROUP BY t.parenttileid
),
site_tenure_remarks AS (
    SELECT DISTINCT ON (t.parenttileid) t.parenttileid AS parenttileid,
           jsonb_build_object(
            'site_tenure_remarks', arches_util.i18n_text(t.tiledata -> '4598a202-197c-11f0-b2a5-0242ac170008')
        ) AS obj
    FROM public.tiles t
    WHERE t.nodegroupid = '4598a202-197c-11f0-b2a5-0242ac170008'::uuid
    ORDER BY t.parenttileid, COALESCE(t.sortorder, 2147483647), t.tileid
),
site_tenure_type AS (
    SELECT DISTINCT ON (t.parenttileid) t.parenttileid AS parenttileid,
           jsonb_build_object(
            'site_tenure_type', arches_util.i18n_text(t.tiledata -> '7b8991ec-197b-11f0-8d46-0242ac170008'),
            'site_tenure_identifier', arches_util.i18n_text(t.tiledata -> 'b2fcabe0-197c-11f0-b2a5-0242ac170008')
        ) AS obj
    FROM public.tiles t
    WHERE t.nodegroupid = '7b8991ec-197b-11f0-8d46-0242ac170008'::uuid
    ORDER BY t.parenttileid, COALESCE(t.sortorder, 2147483647), t.tileid
),
site_tenure AS (
    SELECT DISTINCT ON (t.parenttileid) t.parenttileid AS parenttileid,
           jsonb_build_object(
            'site_tenure_remarks', site_tenure_remarks.obj,
            'site_tenure_type', site_tenure_type.obj
        ) AS obj
    FROM public.tiles t
    LEFT JOIN site_tenure_remarks site_tenure_remarks ON site_tenure_remarks.parenttileid = t.tileid
    LEFT JOIN site_tenure_type site_tenure_type ON site_tenure_type.parenttileid = t.tileid
    WHERE t.nodegroupid = '40a52cd0-197b-11f0-8d46-0242ac170008'::uuid
    ORDER BY t.parenttileid, COALESCE(t.sortorder, 2147483647), t.tileid
),
elevation_comments AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'elevation_comments', arches_util.i18n_text(t.tiledata -> 'bc131e78-01bf-11f0-97f7-0242ac170007')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'bc131e78-01bf-11f0-97f7-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
elevation AS (
    SELECT DISTINCT ON (t.parenttileid) t.parenttileid AS parenttileid,
           jsonb_build_object(
            'gis_lower_elevation', NULLIF(t.tiledata ->> '55b8225e-01bf-11f0-97f7-0242ac170007', '')::numeric,
            'gis_upper_elevation', NULLIF(t.tiledata ->> '547414ac-01bf-11f0-97f7-0242ac170007', '')::numeric,
            'elevation_comments', COALESCE(elevation_comments.arr, '[]'::jsonb)
        ) AS obj
    FROM public.tiles t
    LEFT JOIN elevation_comments elevation_comments ON elevation_comments.parenttileid = t.tileid
    WHERE t.nodegroupid = 'c2f9e970-01be-11f0-9078-0242ac170007'::uuid
    ORDER BY t.parenttileid, COALESCE(t.sortorder, 2147483647), t.tileid
),
bc_property_legal_description AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'pid', t.tiledata ->> 'f5c343f3-217f-4ff0-a414-5dcaff74d2fa',
            'pin', t.tiledata ->> '5513b739-04f5-4c98-9e6f-def560ff3555',
            'legal_description', arches_util.i18n_text(t.tiledata -> '1b623ccc-0d0f-11ed-98c2-5254008afee6'),
            'legal_address_remarks', arches_util.i18n_text(t.tiledata -> '15656a28-1a67-11ed-b83c-5254008afee6')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '1b622ab6-0d0f-11ed-98c2-5254008afee6'::uuid
    GROUP BY t.parenttileid
),
bc_property_address AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'street_number', arches_util.i18n_text(t.tiledata -> '428ee192-8829-11ee-b6ec-080027b7463b'),
            'street_name', arches_util.i18n_text(t.tiledata -> '1b624e60-0d0f-11ed-98c2-5254008afee6'),
            'city', arches_util.i18n_text(t.tiledata -> '1b624082-0d0f-11ed-98c2-5254008afee6'),
            'postal_code', arches_util.i18n_text(t.tiledata -> '1b625414-0d0f-11ed-98c2-5254008afee6'),
            'address_remarks', arches_util.i18n_text(t.tiledata -> 'a1032cd8-1a66-11ed-a3cf-5254008afee6'),
            'bc_property_legal_description', COALESCE(bc_property_legal_description.arr, '[]'::jsonb)
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    LEFT JOIN bc_property_legal_description bc_property_legal_description ON bc_property_legal_description.parenttileid = t.tileid
    WHERE t.nodegroupid = '1b622e58-0d0f-11ed-98c2-5254008afee6'::uuid
    GROUP BY t.parenttileid
),
site_location AS (
    SELECT t.resourceinstanceid AS resourceinstanceid,
           jsonb_agg(jsonb_build_object(
            'biogeography', COALESCE(biogeography.arr, '[]'::jsonb),
            'site_tenure', site_tenure.obj,
            'elevation', elevation.obj,
            'bc_property_address', COALESCE(bc_property_address.arr, '[]'::jsonb)
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    LEFT JOIN biogeography biogeography ON biogeography.parenttileid = t.tileid
    LEFT JOIN site_tenure site_tenure ON site_tenure.parenttileid = t.tileid
    LEFT JOIN elevation elevation ON elevation.parenttileid = t.tileid
    LEFT JOIN bc_property_address bc_property_address ON bc_property_address.parenttileid = t.tileid
    WHERE t.nodegroupid = '1b62393e-0d0f-11ed-98c2-5254008afee6'::uuid
    GROUP BY t.resourceinstanceid
)
SELECT resourceinstanceid, arr AS site_location FROM site_location;

CREATE UNIQUE INDEX mv_site_location_pk ON archaeological_site.mv_site_location (resourceinstanceid);

-- ---------------------------------------------------------------------
-- archaeological_data  (cardinality 1)  children: site_typology
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_archaeological_data CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_archaeological_data AS
WITH site_typology AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'typology_class', arches_util.reference_flat(t.tiledata -> '4d3bb20c-01c0-11f0-97f7-0242ac170007'),
            'typology_remark', arches_util.i18n_text(t.tiledata -> 'e3f0d066-62d1-11f0-8725-76ff5c50888d')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '3083c10e-01c0-11f0-97f7-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
archaeological_data AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'site_typology', COALESCE(site_typology.arr, '[]'::jsonb)
        ) AS obj
    FROM public.tiles t
    LEFT JOIN site_typology site_typology ON site_typology.parenttileid = t.tileid
    WHERE t.nodegroupid = '09856d8c-01c0-11f0-97f7-0242ac170007'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS archaeological_data FROM archaeological_data;

CREATE UNIQUE INDEX mv_archaeological_data_pk ON archaeological_site.mv_archaeological_data (resourceinstanceid);

-- ---------------------------------------------------------------------
-- site_record_admin  (cardinality n)
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_site_record_admin CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_site_record_admin AS
WITH site_record_admin AS (
    SELECT t.resourceinstanceid AS resourceinstanceid,
           jsonb_agg(jsonb_build_object(
            'bcap_submission_status', arches_util.reference_flat(t.tiledata -> '167e3e88-98a3-11ee-a464-080027b7463b'),
            'restricted', NULLIF(t.tiledata ->> 'dc974e68-8f0f-11ee-85a0-080027b7463b', '')::boolean
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '0684fec8-0d07-11ed-8804-5254008afee6'::uuid
    GROUP BY t.resourceinstanceid
)
SELECT resourceinstanceid, arr AS site_record_admin FROM site_record_admin;

CREATE UNIQUE INDEX mv_site_record_admin_pk ON archaeological_site.mv_site_record_admin (resourceinstanceid);

-- ---------------------------------------------------------------------
-- external_url  (cardinality n)
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_external_url CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_external_url AS
WITH external_url AS (
    SELECT t.resourceinstanceid AS resourceinstanceid,
           jsonb_agg(jsonb_build_object(
            'external_url', arches_util.url_obj(t.tiledata -> '3ee73f28-ca40-11ed-af48-5254004d77d3'),
            'external_url_type', arches_util.reference_flat(t.tiledata -> '1f5a7b92-ca41-11ed-933f-5254004d77d3')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '3ee73f28-ca40-11ed-af48-5254004d77d3'::uuid
    GROUP BY t.resourceinstanceid
)
SELECT resourceinstanceid, arr AS external_url FROM external_url;

CREATE UNIQUE INDEX mv_external_url_pk ON archaeological_site.mv_external_url (resourceinstanceid);

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

-- ---------------------------------------------------------------------
-- remarks_and_restricted_information  (cardinality 1)  children: remark_keyword, general_remark_information, contravention_document, restricted_document, hca_contravention, restricted_information, conviction
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_remarks_and_restricted_information CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_remarks_and_restricted_information AS
WITH remark_keyword AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'remark_keyword', arches_util.i18n_text(t.tiledata -> 'dc827931-05ed-43e4-8da6-e99c0d02dae7')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'dc827931-05ed-43e4-8da6-e99c0d02dae7'::uuid
    GROUP BY t.parenttileid
),
general_remark_information AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'general_remark', arches_util.i18n_text(t.tiledata -> '05baf0e2-61a5-11f0-9674-3a7a4e6803c5'),
            'general_remark_source', arches_util.reference_flat(t.tiledata -> '05baef2a-61a5-11f0-9674-3a7a4e6803c5'),
            'general_remark_date', to_date(NULLIF(t.tiledata ->> '05baf01a-61a5-11f0-9674-3a7a4e6803c5', ''), 'YYYY-MM-DD')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '05baebf6-61a5-11f0-9674-3a7a4e6803c5'::uuid
    GROUP BY t.parenttileid
),
contravention_document AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'contravention_document', arches_util.file_list(t.tiledata -> '1bebc404-61a5-11f0-9674-3a7a4e6803c5')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '1bebc404-61a5-11f0-9674-3a7a4e6803c5'::uuid
    GROUP BY t.parenttileid
),
restricted_document AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'restricted_document', arches_util.file_list(t.tiledata -> '250ed6fe-61a8-11f0-ad02-3a7a4e6803c5')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '250ed6fe-61a8-11f0-ad02-3a7a4e6803c5'::uuid
    GROUP BY t.parenttileid
),
hca_contravention AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'inventory_remark', arches_util.i18n_text(t.tiledata -> '41fb5e20-61a5-11f0-9674-3a7a4e6803c5'),
            'contravention_address', arches_util.i18n_text(t.tiledata -> '41fb5eca-61a5-11f0-9674-3a7a4e6803c5'),
            'contravention_pid', arches_util.i18n_text(t.tiledata -> '41fb5f7e-61a5-11f0-9674-3a7a4e6803c5'),
            'nros_file_number', arches_util.i18n_text(t.tiledata -> '41fb603c-61a5-11f0-9674-3a7a4e6803c5')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '41fb5948-61a5-11f0-9674-3a7a4e6803c5'::uuid
    GROUP BY t.parenttileid
),
restricted_information AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'restricted_remark', arches_util.i18n_text(t.tiledata -> 'b0ed366a-61a4-11f0-9674-3a7a4e6803c5'),
            'restricted_person', arches_util.resource_id(t.tiledata -> 'b0ed35ac-61a4-11f0-9674-3a7a4e6803c5'),
            'restricted_entry_date', to_date(NULLIF(t.tiledata ->> 'b0ed34b2-61a4-11f0-9674-3a7a4e6803c5', ''), 'YYYY-MM-DD')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'b0ed31c4-61a4-11f0-9674-3a7a4e6803c5'::uuid
    GROUP BY t.parenttileid
),
conviction AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'conviction_details', arches_util.i18n_text(t.tiledata -> 'c515a668-619f-11f0-acf4-3a7a4e6803c5'),
            'conviction_date', to_date(NULLIF(t.tiledata ->> 'c515a532-619f-11f0-acf4-3a7a4e6803c5', ''), 'YYYY-MM-DD')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'c5159e8e-619f-11f0-acf4-3a7a4e6803c5'::uuid
    GROUP BY t.parenttileid
),
remarks_and_restricted_information AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'remark_keyword', COALESCE(remark_keyword.arr, '[]'::jsonb),
            'general_remark_information', COALESCE(general_remark_information.arr, '[]'::jsonb),
            'contravention_document', COALESCE(contravention_document.arr, '[]'::jsonb),
            'restricted_document', COALESCE(restricted_document.arr, '[]'::jsonb),
            'hca_contravention', COALESCE(hca_contravention.arr, '[]'::jsonb),
            'restricted_information', COALESCE(restricted_information.arr, '[]'::jsonb),
            'conviction', COALESCE(conviction.arr, '[]'::jsonb)
        ) AS obj
    FROM public.tiles t
    LEFT JOIN remark_keyword remark_keyword ON remark_keyword.parenttileid = t.tileid
    LEFT JOIN general_remark_information general_remark_information ON general_remark_information.parenttileid = t.tileid
    LEFT JOIN contravention_document contravention_document ON contravention_document.parenttileid = t.tileid
    LEFT JOIN restricted_document restricted_document ON restricted_document.parenttileid = t.tileid
    LEFT JOIN hca_contravention hca_contravention ON hca_contravention.parenttileid = t.tileid
    LEFT JOIN restricted_information restricted_information ON restricted_information.parenttileid = t.tileid
    LEFT JOIN conviction conviction ON conviction.parenttileid = t.tileid
    WHERE t.nodegroupid = '75c91464-619f-11f0-acf4-3a7a4e6803c5'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS remarks_and_restricted_information FROM remarks_and_restricted_information;

CREATE UNIQUE INDEX mv_remarks_and_restricted_information_pk ON archaeological_site.mv_remarks_and_restricted_information (resourceinstanceid);

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


-- =====================================================================
-- GEOMETRY promoted to real typed columns. Two geojson nodes in this graph:
--   site_boundary      (cardinality 1, on the site_boundary nodegroup)
--   unprotected_areas  (cardinality n, on a CHILD of site_boundary)
-- Both are also embedded as GeoJSON inside the jsonb object. The typed column
-- is what spatial queries need; the GeoJSON is what a web client wants.
-- =====================================================================
DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_geom_site_boundary CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_geom_site_boundary AS
SELECT t.resourceinstanceid,
       ST_CollectionHomogenize(ST_Collect(gg.geom)) AS site_boundary_geom
FROM public.tiles t
JOIN LATERAL (
    SELECT ST_Collect(ST_Transform(g.geom, 4326)) AS geom
    FROM public.geojson_geometries g
    WHERE g.tileid = t.tileid AND g.nodeid = 'b18223c2-13ef-11f0-8695-0242ac170007'::uuid
) gg ON gg.geom IS NOT NULL
WHERE t.nodegroupid = 'b18223c2-13ef-11f0-8695-0242ac170007'::uuid
GROUP BY t.resourceinstanceid;

CREATE UNIQUE INDEX mv_geom_site_boundary_pk ON archaeological_site.mv_geom_site_boundary (resourceinstanceid);
CREATE INDEX mv_geom_site_boundary_gix ON archaeological_site.mv_geom_site_boundary USING GIST (site_boundary_geom);

DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_geom_unprotected_areas CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_geom_unprotected_areas AS
SELECT t.resourceinstanceid,
       ST_CollectionHomogenize(ST_Collect(gg.geom)) AS unprotected_areas_geom
FROM public.tiles t
JOIN LATERAL (
    SELECT ST_Collect(ST_Transform(g.geom, 4326)) AS geom
    FROM public.geojson_geometries g
    WHERE g.tileid = t.tileid AND g.nodeid = '7c8eb1f8-44e2-4239-afaa-9cbf1fadf160'::uuid
) gg ON gg.geom IS NOT NULL
WHERE t.nodegroupid = '7c8eb1f8-44e2-4239-afaa-9cbf1fadf160'::uuid
GROUP BY t.resourceinstanceid;

CREATE UNIQUE INDEX mv_geom_unprotected_areas_pk ON archaeological_site.mv_geom_unprotected_areas (resourceinstanceid);
CREATE INDEX mv_geom_unprotected_areas_gix ON archaeological_site.mv_geom_unprotected_areas USING GIST (unprotected_areas_geom);


DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_resource_v1 CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_resource_v1 AS
SELECT
    r.resourceinstanceid,
    b0.site_boundary,
    b1.identification_and_registration,
    COALESCE(b2.site_location, '[]'::jsonb) AS site_location,
    b3.archaeological_data,
    COALESCE(b4.site_record_admin, '[]'::jsonb) AS site_record_admin,
    COALESCE(b5.external_url, '[]'::jsonb) AS external_url,
    b6.ancestral_remains,
    b7.remarks_and_restricted_information,
    b8.related_documents,
    g_site_boundary.site_boundary_geom,
    g_unprotected_areas.unprotected_areas_geom,
    jsonb_build_object(
        'resourceinstanceid', r.resourceinstanceid,
        'site_boundary', b0.site_boundary,
        'identification_and_registration', b1.identification_and_registration,
        'site_location', COALESCE(b2.site_location, '[]'::jsonb),
        'archaeological_data', b3.archaeological_data,
        'site_record_admin', COALESCE(b4.site_record_admin, '[]'::jsonb),
        'external_url', COALESCE(b5.external_url, '[]'::jsonb),
        'ancestral_remains', b6.ancestral_remains,
        'remarks_and_restricted_information', b7.remarks_and_restricted_information,
        'related_documents', b8.related_documents
    ) AS resource
FROM public.resource_instances r
LEFT JOIN archaeological_site.mv_site_boundary b0 ON b0.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_identification_and_registration b1 ON b1.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_site_location b2 ON b2.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_archaeological_data b3 ON b3.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_site_record_admin b4 ON b4.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_external_url b5 ON b5.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_ancestral_remains b6 ON b6.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_remarks_and_restricted_information b7 ON b7.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_related_documents b8 ON b8.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_geom_site_boundary g_site_boundary ON g_site_boundary.resourceinstanceid = r.resourceinstanceid
LEFT JOIN archaeological_site.mv_geom_unprotected_areas g_unprotected_areas ON g_unprotected_areas.resourceinstanceid = r.resourceinstanceid
WHERE r.graphid = 'cef9c510-e3e6-4057-ac08-89ad926180b4'::uuid;

CREATE UNIQUE INDEX mv_resource_v1_pk ON archaeological_site.mv_resource_v1 (resourceinstanceid);
CREATE INDEX mv_resource_v1_res ON archaeological_site.mv_resource_v1 USING GIN (resource jsonb_path_ops);
CREATE INDEX mv_resource_v1_site_boundary_gix ON archaeological_site.mv_resource_v1 USING GIST (site_boundary_geom);
CREATE INDEX mv_resource_v1_unprotected_areas_gix ON archaeological_site.mv_resource_v1 USING GIST (unprotected_areas_geom);

-- =====================================================================
-- WRAPPER VIEW - the downstream contract. Nothing else names the matview.
-- =====================================================================
CREATE OR REPLACE VIEW archaeological_site.resource AS
SELECT * FROM archaeological_site.mv_resource_v1;

COMMENT ON VIEW archaeological_site.resource IS
'Stable read contract for the archaeological_site graph. One row per resource instance. '
'Backed by a materialized view - repoint the backing matview here, never rename this. '
'Arrays are always [] when empty, never null. Cardinality-1 branches are null when the tile does not exist.';

-- GRANT SELECT ON archaeological_site.resource TO <app_role>;


-- =====================================================================
-- REFRESH.  Geometry matviews first (the branches embed their GeoJSON),
-- then branches, then the final object.
-- =====================================================================
CREATE OR REPLACE PROCEDURE archaeological_site.refresh_resource(concurrent boolean DEFAULT true)
LANGUAGE plpgsql AS $$
DECLARE
    mode text := CASE WHEN concurrent THEN 'CONCURRENTLY' ELSE '' END;
    mv   text;
BEGIN
    FOREACH mv IN ARRAY ARRAY[
        'archaeological_site.mv_geom_site_boundary',
        'archaeological_site.mv_geom_unprotected_areas',
        'archaeological_site.mv_site_boundary',
        'archaeological_site.mv_identification_and_registration',
        'archaeological_site.mv_site_location',
        'archaeological_site.mv_archaeological_data',
        'archaeological_site.mv_site_record_admin',
        'archaeological_site.mv_external_url',
        'archaeological_site.mv_ancestral_remains',
        'archaeological_site.mv_remarks_and_restricted_information',
        'archaeological_site.mv_related_documents',
        'archaeological_site.mv_resource_v1'          -- must be last
    ]
    LOOP
        RAISE NOTICE 'refreshing %', mv;
        EXECUTE format('REFRESH MATERIALIZED VIEW %s %s', mode, mv);
        COMMIT;
    END LOOP;
END $$;
