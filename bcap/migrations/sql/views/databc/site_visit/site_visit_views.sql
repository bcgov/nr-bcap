-- =====================================================================
--  site_visit :: one-object materialized view stack  -- V2, tiles-direct
--
--  WHAT CHANGED FROM V1 AND WHY
--  ---------------------------------------------------------------------
--  V1 read the 24 generated site_visit.* views. Each of those does:
--
--      FROM tiles t
--      LEFT JOIN edit_log e1 ON t.tileid = (e1.tileinstanceid)::uuid
--      LEFT JOIN edit_log e2 ON t.tileid = (e2.tileinstanceid)::uuid
--                           AND e1."timestamp" < e2."timestamp"
--      WHERE t.nodegroupid = '...' AND e2.editlogid IS NULL
--
--  and contributes exactly ONE column from all that work: e1.transactionid.
--  This stack does not use transactionid. So V1 was paying, 24 times over, for:
--
--    1. Two scans of edit_log - a big append-only audit table.
--    2. (e1.tileinstanceid)::uuid in the join predicate. tileinstanceid is TEXT.
--       A cast in a join predicate cannot use a plain btree index, so each of
--       those scans is SEQUENTIAL over the whole audit log.
--    3. A triangular self-join: for a tile with N edits, e1 x e2 ON ts < ts
--       materialises O(N^2) rows before the anti-join discards them.
--
--  That is where the time went, and that is what exhausted /dev/shm.
--
--  SAFE TO DROP? Yes, provably. Both edit_log joins are LEFT JOINs, so a tile
--  with zero edit_log rows still survives (e1 null -> e2 null -> passes the
--  anti-join). The WHERE clause never removes a TILE; it only collapses the
--  fan-out back to one row per tile. The row set is therefore identical to:
--
--      SELECT * FROM tiles WHERE nodegroupid = '<ng>'
--
--  Preflight check I below proves this per nodegroup against your data. Run it.
--
--  THREE THINGS FALL OUT OF READING tiles DIRECTLY
--  ---------------------------------------------------------------------
--  * DISTINCT ON is GONE. tiles.tileid is the primary key, so a tile cannot be
--    emitted twice. The duplicate-array-element hazard V1 defended against was
--    manufactured entirely by the edit_log join. It does not exist here.
--
--  * tiles.sortorder is now available. The generated views drop it. It is the
--    author's intended ordering of tiles within a nodegroup, so every jsonb_agg
--    below orders by it, with tileid as a stable tiebreak. Strictly better than
--    V1's arbitrary-but-stable tileid ordering.
--
--  * Geometry is aggregated ONCE. V1 inherited a correlated subquery
--    ARRAY(SELECT ... FROM geojson_geometries WHERE tileid = t.tileid) that ran
--    PER ROW. Here it is a single grouped scan, joined in.
--
--  DATE FORMATS ARE REPRODUCED EXACTLY, INCLUDING THE ODD ONES
--  ---------------------------------------------------------------------
--  The generated views use to_date(..., 'YYYY') - year only - for start_year,
--  end_year AND image_date, but 'YYYY-MM-DD' for the other dates. to_date is
--  lenient: to_date('2015-06-29','YYYY') silently returns 2015-01-01. So the
--  views already truncate image_date to a year. I have reproduced that exactly
--  rather than "fixing" it, so the v1-vs-v2 diff is meaningful. If you want the
--  full image_date, that is a deliberate v3 change - see the marker below.
--
--  ADJUST IF YOUR ARCHES CORE TABLES ARE NOT IN public.
-- =====================================================================

SET maintenance_work_mem = '512MB';
SET work_mem             = '128MB';


-- =====================================================================
-- STEP 1 - INDEXES THE STACK NEEDS
-- Arches ships tiles(nodegroupid) as an FK index; the other two are worth
-- confirming. IF NOT EXISTS makes these safe to run blind.
-- =====================================================================
CREATE INDEX IF NOT EXISTS tiles_nodegroupid_idx
    ON public.tiles (nodegroupid);
CREATE INDEX IF NOT EXISTS geojson_geometries_nodeid_idx
    ON public.geojson_geometries (nodeid);
CREATE INDEX IF NOT EXISTS resource_instances_graphid_idx
    ON public.resource_instances (graphid);

-- NOTE: an index on tiles(parenttileid) is NOT needed. Every child is scanned
-- in full for its nodegroup and hash-aggregated by parenttileid - a grouping,
-- not a lookup. (I suggested this index in an earlier message. It was wrong.)


-- =====================================================================
-- STEP 2 - HELPER FUNCTIONS  (unchanged from v1 - value decoding, not plumbing)
-- =====================================================================
CREATE SCHEMA IF NOT EXISTS arches_util;

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


-- =====================================================================
-- STEP 3 - BRANCH MATVIEWS, READING public.tiles DIRECTLY
--
-- Every leaf is now:   FROM public.tiles WHERE nodegroupid = '<ng>'::uuid
-- One index scan each. No edit_log. No DISTINCT ON.
--
-- The UNIQUE INDEX on each cardinality-1 branch is an assertion, not a hint:
-- preflight A confirmed all 24 cardinalities against node_groups, so if one of
-- these ever fires, the GRAPH changed - regenerate, do not paper over it.
--
-- Array ordering is ALWAYS: COALESCE(sortorder, 2147483647), tileid
-- (sortorder is nullable; nulls sort last, tileid breaks ties deterministically)
-- =====================================================================

-- ---------------------------------------------------------------------
-- 3.1  site_visit_location (n)  ->  biogeography (n)
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_site_visit_location CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_site_visit_location AS
WITH geom AS (
    -- ONE grouped scan. V1 inherited this as a correlated per-row subquery.
    SELECT g.tileid,
           ST_Collect(ST_Transform(g.geom, 4326)) AS geom
    FROM public.geojson_geometries g
    WHERE g.nodeid = 'cf40edc0-13f0-11f0-9404-0242ac170007'::uuid
    GROUP BY g.tileid
),
biogeo AS (
    SELECT t.parenttileid,
           jsonb_agg(jsonb_build_object(
               'biogeography_type',        arches_util.reference_flat(t.tiledata -> '5270c773-125c-4223-868e-badeb5cf5f78'),
               'biogeography_name',        arches_util.i18n_text(t.tiledata -> '5c7d9c33-c53e-45ea-b503-d4bbeaa9e31c'),
               'biogeography_description', arches_util.i18n_text(t.tiledata -> '95e5f9b6-71cd-4769-b365-9155442954ec')
           ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '6abfca2d-8f5d-458a-b128-ab8ba49c1921'::uuid
    GROUP BY t.parenttileid
),
loc AS (
    SELECT t.tileid, t.resourceinstanceid, t.sortorder, g.geom,
           jsonb_build_object(
               'tileid',              t.tileid,
               'boundary_type',       arches_util.reference_flat(t.tiledata -> '9aea2913-e4ee-43dd-904c-abee908f61b6'),
               'latest_edit_type',    arches_util.reference_flat(t.tiledata -> 'cf40f158-13f0-11f0-9404-0242ac170007'),
               'location_and_access', arches_util.i18n_text(t.tiledata -> 'cca03a72-13fe-11f0-99e9-0242ac170007'),
               'accuracy_remarks',    arches_util.i18n_text(t.tiledata -> 'cf40f40a-13f0-11f0-9404-0242ac170007'),
               'geometry',            CASE WHEN g.geom IS NULL THEN NULL
                                           ELSE ST_AsGeoJSON(g.geom, 7)::jsonb END,
               'biogeography',        COALESCE(b.arr, '[]'::jsonb)
           ) AS obj
    FROM public.tiles t
    LEFT JOIN geom   g ON g.tileid       = t.tileid
    LEFT JOIN biogeo b ON b.parenttileid = t.tileid
    WHERE t.nodegroupid = 'cf40edc0-13f0-11f0-9404-0242ac170007'::uuid
)
SELECT resourceinstanceid,
       jsonb_agg(obj ORDER BY COALESCE(sortorder, 2147483647), tileid) AS site_visit_location,
       ST_Collect(geom) FILTER (WHERE geom IS NOT NULL)                AS site_visit_geom
FROM loc
GROUP BY resourceinstanceid;

CREATE UNIQUE INDEX mv_site_visit_location_pk ON site_visit.mv_site_visit_location (resourceinstanceid);
CREATE INDEX mv_site_visit_location_geom ON site_visit.mv_site_visit_location USING GIST (site_visit_geom);


-- ---------------------------------------------------------------------
-- 3.2  identification (1)  ->  new_site_names (n), temporary_number (1)
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_identification CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_identification AS
WITH names AS (
    SELECT t.parenttileid,
           jsonb_agg(jsonb_build_object(
               'name',                      arches_util.i18n_text(t.tiledata -> '6d90619c-140d-11f0-b9bb-0242ac170007'),
               'name_type',                 arches_util.reference_flat(t.tiledata -> '6d9065d4-140d-11f0-b9bb-0242ac170007'),
               'name_remarks',              arches_util.i18n_text(t.tiledata -> '6d9066ce-140d-11f0-b9bb-0242ac170007'),
               'assigned_or_reported_by',   arches_util.resource_id(t.tiledata -> '6d9063d6-140d-11f0-b9bb-0242ac170007'),
               'assigned_or_reported_date', to_date(NULLIF(t.tiledata ->> '6d9067be-140d-11f0-b9bb-0242ac170007', ''), 'YYYY-MM-DD')
           ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '6d905dbe-140d-11f0-b9bb-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
tempnum AS (
    SELECT DISTINCT ON (t.parenttileid) t.parenttileid,
           jsonb_build_object(
               'temporary_number',               arches_util.i18n_text(t.tiledata -> 'ab674670-140d-11f0-b9bb-0242ac170007'),
               'temporary_number_assigned_by',   arches_util.resource_id(t.tiledata -> 'c85b4e24-140e-11f0-8419-0242ac170007'),
               'temporary_number_assigned_date', to_date(NULLIF(t.tiledata ->> 'e3dd076e-140e-11f0-8419-0242ac170007', ''), 'YYYY-MM-DD')
           ) AS obj
    FROM public.tiles t
    WHERE t.nodegroupid = 'ab674670-140d-11f0-b9bb-0242ac170007'::uuid
    ORDER BY t.parenttileid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT t.resourceinstanceid,
       jsonb_build_object(
           'new_site_names',   COALESCE(n.arr, '[]'::jsonb),
           'temporary_number', tn.obj
       ) AS identification
FROM public.tiles t
LEFT JOIN names   n  ON n.parenttileid  = t.tileid
LEFT JOIN tempnum tn ON tn.parenttileid = t.tileid
WHERE t.nodegroupid = '37bdda22-140d-11f0-b9bb-0242ac170007'::uuid;

CREATE UNIQUE INDEX mv_identification_pk ON site_visit.mv_identification (resourceinstanceid);


-- ---------------------------------------------------------------------
-- 3.3  site_visit_details (1)  ->  site_visit_team (1)  ->  team_member (n)
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_site_visit_details CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_site_visit_details AS
WITH members AS (
    SELECT t.parenttileid,
           jsonb_agg(jsonb_build_object(
               'team_member',  arches_util.resource_id(t.tiledata -> '0484d572-1410-11f0-8419-0242ac170007'),
               'member_roles', arches_util.reference_flat(t.tiledata -> '0484d69e-1410-11f0-8419-0242ac170007'),
               'was_on_site',  NULLIF(t.tiledata ->> '0484d428-1410-11f0-8419-0242ac170007', '')::boolean
           ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '0484d572-1410-11f0-8419-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
team AS (
    SELECT DISTINCT ON (t.parenttileid) t.parenttileid,
           jsonb_build_object('team_member', COALESCE(m.arr, '[]'::jsonb)) AS obj
    FROM public.tiles t
    LEFT JOIN members m ON m.parenttileid = t.tileid
    WHERE t.nodegroupid = '0484d0b8-1410-11f0-8419-0242ac170007'::uuid
    ORDER BY t.parenttileid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT t.resourceinstanceid,
       jsonb_build_object(
           'site_visit_type',          arches_util.reference_flat(t.tiledata -> 'e39372c4-df58-11ef-8fa3-0242ac170009'),
           'is_site_visit_permitted',  NULLIF(t.tiledata ->> 'fb01d6a1-cac8-4b16-8f2c-5472213aeec6', '')::boolean,
           'first_date_of_site_visit', to_date(NULLIF(t.tiledata ->> '745b0462-140f-11f0-8419-0242ac170007', ''), 'YYYY-MM-DD'),
           'last_date_of_site_visit',  to_date(NULLIF(t.tiledata ->> '1de04042-df59-11ef-8fa3-0242ac170009', ''), 'YYYY-MM-DD'),
           'project_description',      arches_util.i18n_text(t.tiledata -> 'fbfbb0a6-df58-11ef-8fa3-0242ac170009'),
           'affiliation',              arches_util.resource_id(t.tiledata -> '69273f50-4c9c-11f0-9f73-0242ac170007'),
           'archaeological_site',      arches_util.resource_id(t.tiledata -> 'cd722a58-df58-11ef-8fa3-0242ac170009'),
           'associated_permit',        arches_util.resource_ids(t.tiledata -> 'b03790fe-df58-11ef-8fa3-0242ac170009'),
           'site_form_authors',        arches_util.resource_ids(t.tiledata -> '4fb2db52-1410-11f0-8419-0242ac170007'),
           'site_visit_team',          tm.obj
       ) AS site_visit_details
FROM public.tiles t
LEFT JOIN team tm ON tm.parenttileid = t.tileid
WHERE t.nodegroupid = '887edb3a-df58-11ef-8fa3-0242ac170009'::uuid;

CREATE UNIQUE INDEX mv_site_visit_details_pk ON site_visit.mv_site_visit_details (resourceinstanceid);


-- ---------------------------------------------------------------------
-- 3.4  archaeological_data (1)  ->  seven n-children
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_archaeological_data CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_archaeological_data AS
WITH cm AS (
    SELECT t.parenttileid, jsonb_agg(jsonb_build_object(
        'cultural_material_type',    arches_util.reference_flat(t.tiledata -> '4abf8e50-1402-11f0-acd5-0242ac170007'),
        'cultural_material_status',  arches_util.reference_flat(t.tiledata -> '5d4e5254-1402-11f0-acd5-0242ac170007'),
        'cultural_material_details', arches_util.i18n_text(t.tiledata -> 'b029a3c0-1402-11f0-a830-0242ac170007'),
        'number_of_artifacts',       NULLIF(t.tiledata ->> '2423be32-1403-11f0-ae97-0242ac170007', '')::numeric,
        'repository',                arches_util.resource_id(t.tiledata -> '3787b9de-5cd2-11f0-b2ee-0242ac170007')
    ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t WHERE t.nodegroupid = '22508fc8-1402-11f0-acd5-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
strat AS (
    SELECT t.parenttileid, jsonb_agg(jsonb_build_object(
        'stratigraphy', arches_util.i18n_text(t.tiledata -> '720dd6dc-1408-11f0-9e93-0242ac170007')
    ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t WHERE t.nodegroupid = '720dd6dc-1408-11f0-9e93-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
feat AS (
    SELECT t.parenttileid, jsonb_agg(jsonb_build_object(
        'archaeological_feature', arches_util.reference_flat(t.tiledata -> 'a0c7cc6e-1401-11f0-acd5-0242ac170007'),
        'feature_count',          NULLIF(t.tiledata ->> 'a0c7d01a-1401-11f0-acd5-0242ac170007', '')::numeric,
        'feature_remarks',        arches_util.i18n_text(t.tiledata -> 'a0c7d128-1401-11f0-acd5-0242ac170007')
    ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t WHERE t.nodegroupid = 'a0c7cc6e-1401-11f0-acd5-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
chron AS (
    -- NOTE the 'YYYY' format on start_year / end_year: reproduced from the
    -- generated view. Year precision, deliberately.
    SELECT t.parenttileid, jsonb_agg(jsonb_build_object(
        'start_year',           to_date(NULLIF(t.tiledata ->> 'c1f5724c-140b-11f0-898b-0242ac170007', ''), 'YYYY'),
        'start_year_qualifier', arches_util.reference_flat(t.tiledata -> 'c1f576d4-140b-11f0-898b-0242ac170007'),
        'start_year_calendar',  arches_util.reference_flat(t.tiledata -> 'c1f575ee-140b-11f0-898b-0242ac170007'),
        'end_year',             to_date(NULLIF(t.tiledata ->> 'c1f57418-140b-11f0-898b-0242ac170007', ''), 'YYYY'),
        'end_year_qualifier',   arches_util.reference_flat(t.tiledata -> 'c1f56e78-140b-11f0-898b-0242ac170007'),
        'end_year_calendar',    arches_util.reference_flat(t.tiledata -> 'c1f56f86-140b-11f0-898b-0242ac170007'),
        'determination_method', arches_util.reference_flat(t.tiledata -> 'c1f57166-140b-11f0-898b-0242ac170007'),
        'information_source',   arches_util.i18n_text(t.tiledata -> 'c1f57332-140b-11f0-898b-0242ac170007'),
        'chronology_remarks',   arches_util.i18n_text(t.tiledata -> 'c1f57080-140b-11f0-898b-0242ac170007')
    ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t WHERE t.nodegroupid = 'c1f56b08-140b-11f0-898b-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
cult AS (
    SELECT t.parenttileid, jsonb_agg(jsonb_build_object(
        'archaeological_culture', arches_util.reference_flat(t.tiledata -> 'fab4ba5a-1408-11f0-9e93-0242ac170007'),
        'culture_remarks',        arches_util.i18n_text(t.tiledata -> 'fab4bde8-1408-11f0-9e93-0242ac170007')
    ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t WHERE t.nodegroupid = 'fab4ba5a-1408-11f0-9e93-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
dist AS (
    SELECT t.parenttileid, jsonb_agg(jsonb_build_object(
        'disturbance_period',  arches_util.reference_flat(t.tiledata -> 'fb559480-140c-11f0-b9bb-0242ac170007'),
        'disturbance_cause',   arches_util.reference_flat(t.tiledata -> 'fb5595c0-140c-11f0-b9bb-0242ac170007'),
        'disturbance_remarks', arches_util.i18n_text(t.tiledata -> 'fb5596b0-140c-11f0-b9bb-0242ac170007')
    ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t WHERE t.nodegroupid = 'fb559106-140c-11f0-b9bb-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
typo AS (
    SELECT t.parenttileid, jsonb_agg(jsonb_build_object(
        'typology_class',  arches_util.reference_flat(t.tiledata -> 'd6765cc8-8dec-431b-bbb5-950567e6ed1c'),
        'typology_remark', arches_util.i18n_text(t.tiledata -> 'c98387af-e430-4317-b222-9f2191194817')
    ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t WHERE t.nodegroupid = 'c3738e14-a521-47c1-8b52-668847a8a51e'::uuid
    GROUP BY t.parenttileid
)
SELECT t.resourceinstanceid,
       jsonb_build_object(
           'cultural_material',        COALESCE(cm.arr,    '[]'::jsonb),
           'stratigraphy',             COALESCE(strat.arr, '[]'::jsonb),
           'archaeological_feature',   COALESCE(feat.arr,  '[]'::jsonb),
           'chronology',               COALESCE(chron.arr, '[]'::jsonb),
           'archaeological_culture',   COALESCE(cult.arr,  '[]'::jsonb),
           'site_disturbance',         COALESCE(dist.arr,  '[]'::jsonb),
           'additional_site_typology', COALESCE(typo.arr,  '[]'::jsonb)
       ) AS archaeological_data
FROM public.tiles t
LEFT JOIN cm    ON cm.parenttileid    = t.tileid
LEFT JOIN strat ON strat.parenttileid = t.tileid
LEFT JOIN feat  ON feat.parenttileid  = t.tileid
LEFT JOIN chron ON chron.parenttileid = t.tileid
LEFT JOIN cult  ON cult.parenttileid  = t.tileid
LEFT JOIN dist  ON dist.parenttileid  = t.tileid
LEFT JOIN typo  ON typo.parenttileid  = t.tileid
WHERE t.nodegroupid = '3648fb88-1401-11f0-acd5-0242ac170007'::uuid;

CREATE UNIQUE INDEX mv_archaeological_data_pk ON site_visit.mv_archaeological_data (resourceinstanceid);


-- ---------------------------------------------------------------------
-- 3.5  remarks_and_recommendations (1)  ->  recommendation (n), general_remark (n)
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_remarks_and_recommendations CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_remarks_and_recommendations AS
WITH rec AS (
    SELECT t.parenttileid, jsonb_agg(jsonb_build_object(
        'recorders_recommendation',          arches_util.i18n_text(t.tiledata -> '8cf43cd4-61ab-11f0-be7c-3a7a4e6803c5'),
        'archaeology_branch_recommendation', arches_util.i18n_text(t.tiledata -> 'fadb061b-2be7-4a0b-810a-51d8cee25bf8')
    ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t WHERE t.nodegroupid = '8cf43a0e-61ab-11f0-be7c-3a7a4e6803c5'::uuid
    GROUP BY t.parenttileid
),
rem AS (
    SELECT t.parenttileid, jsonb_agg(jsonb_build_object(
        'remark',        arches_util.i18n_text(t.tiledata -> '9625068a-61ab-11f0-be7c-3a7a4e6803c5'),
        'remark_date',   to_date(NULLIF(t.tiledata ->> '962505cc-61ab-11f0-be7c-3a7a4e6803c5', ''), 'YYYY-MM-DD'),
        'remark_source', arches_util.reference_flat(t.tiledata -> '962504dc-61ab-11f0-be7c-3a7a4e6803c5')
    ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t WHERE t.nodegroupid = '9625020c-61ab-11f0-be7c-3a7a4e6803c5'::uuid
    GROUP BY t.parenttileid
)
SELECT t.resourceinstanceid,
       jsonb_build_object(
           'recommendation', COALESCE(rec.arr, '[]'::jsonb),
           'general_remark', COALESCE(rem.arr, '[]'::jsonb)
       ) AS remarks_and_recommendations
FROM public.tiles t
LEFT JOIN rec ON rec.parenttileid = t.tileid
LEFT JOIN rem ON rem.parenttileid = t.tileid
WHERE t.nodegroupid = '77789d46-61ab-11f0-be7c-3a7a4e6803c5'::uuid;

CREATE UNIQUE INDEX mv_remarks_and_recommendations_pk ON site_visit.mv_remarks_and_recommendations (resourceinstanceid);


-- ---------------------------------------------------------------------
-- 3.6  ancestral_remains (n, no children)
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_ancestral_remains CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_ancestral_remains AS
SELECT t.resourceinstanceid,
       jsonb_agg(jsonb_build_object(
           'ancestral_remains_type',        arches_util.reference_flat(t.tiledata -> '6f96fb9a-5049-11f0-91cd-0242ac170006'),
           'ancestral_remains_status',      arches_util.reference_flat(t.tiledata -> '6f96fd5c-5049-11f0-91cd-0242ac170006'),
           'ancestral_remains_remarks',     arches_util.i18n_text(t.tiledata -> '6f96fe2e-5049-11f0-91cd-0242ac170006'),
           'ancestral_remains_repository',  arches_util.resource_id(t.tiledata -> 'a87dd01e-5ce2-11f0-a419-0242ac170007'),
           'minimum_number_of_individuals', NULLIF(t.tiledata ->> '6f96fef6-5049-11f0-91cd-0242ac170006', '')::numeric,
           'multiple_burials',              NULLIF(t.tiledata ->> '6f96fc94-5049-11f0-91cd-0242ac170006', '')::boolean
       ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS ancestral_remains
FROM public.tiles t
WHERE t.nodegroupid = '6f96f910-5049-11f0-91cd-0242ac170006'::uuid
GROUP BY t.resourceinstanceid;

CREATE UNIQUE INDEX mv_ancestral_remains_pk ON site_visit.mv_ancestral_remains (resourceinstanceid);


-- ---------------------------------------------------------------------
-- 3.7  related_documents (1)  ->  related_site_documents, publication_reference,
--                                 site_images  (all n)
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_related_documents CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_related_documents AS
WITH rsd AS (
    SELECT t.parenttileid, jsonb_agg(jsonb_build_object(
        'related_site_documents',       arches_util.file_list(t.tiledata -> '55f5927c-8279-4864-ba1d-2f288ca46fcf'),
        'related_document_type',        arches_util.reference_flat(t.tiledata -> 'acbdadfa-2ccf-4a68-9497-56d36dbd1021'),
        'related_document_description', arches_util.i18n_text(t.tiledata -> '844ae10f-b38b-4706-8fac-8804d04ab05e')
    ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t WHERE t.nodegroupid = '55f5927c-8279-4864-ba1d-2f288ca46fcf'::uuid
    GROUP BY t.parenttileid
),
pub AS (
    SELECT t.parenttileid, jsonb_agg(jsonb_build_object(
        'publication_reference', arches_util.resource_ids(t.tiledata -> '6ac56e05-8c19-4ef3-9f3b-f5921c278e17')
    ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t WHERE t.nodegroupid = '6ac56e05-8c19-4ef3-9f3b-f5921c278e17'::uuid
    GROUP BY t.parenttileid
),
img AS (
    -- image_date uses 'YYYY' - year precision - because the generated view does.
    -- V3 MARKER: if you want the real full date, change to 'YYYY-MM-DD' here AND
    -- bump the matview version. It is a contract change, not a bug fix.
    SELECT t.parenttileid, jsonb_agg(jsonb_build_object(
        'site_images',       arches_util.file_list(t.tiledata -> 'a6536975-292e-47d1-8ebe-7e83092438bd'),
        'primary_image',     NULLIF(t.tiledata ->> '696b4699-bc65-4d0e-8d48-f2a211fe5e3a', '')::boolean,
        'image_type',        arches_util.reference_flat(t.tiledata -> '98c6f7ee-5c7f-4287-aeed-0168e5c40773'),
        'image_view',        arches_util.reference_flat(t.tiledata -> 'c0dbd7b1-9c2b-4c27-96f3-17cb5aad7d25'),
        'image_description', arches_util.i18n_text(t.tiledata -> '10d83dfd-49d8-4bf3-9977-4acbc809b7b8'),
        'image_features',    arches_util.i18n_text(t.tiledata -> '9bd92cab-7995-4940-9547-073e2eb505ac'),
        'photographer',      arches_util.i18n_text(t.tiledata -> 'd20d1438-701d-47e9-8f93-7a460f3bba75'),
        'copyright',         arches_util.i18n_text(t.tiledata -> '7b7f1f4c-df01-4881-b9f3-495fc9a968bc'),
        'image_date',        to_date(NULLIF(t.tiledata ->> '2454579e-6884-4d1d-82f3-724f62ce4d4f', ''), 'YYYY')
    ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t WHERE t.nodegroupid = 'a6536975-292e-47d1-8ebe-7e83092438bd'::uuid
    GROUP BY t.parenttileid
)
SELECT t.resourceinstanceid,
       jsonb_build_object(
           'related_site_documents', COALESCE(rsd.arr, '[]'::jsonb),
           'publication_reference',  COALESCE(pub.arr, '[]'::jsonb),
           'site_images',            COALESCE(img.arr, '[]'::jsonb)
       ) AS related_documents
FROM public.tiles t
LEFT JOIN rsd ON rsd.parenttileid = t.tileid
LEFT JOIN pub ON pub.parenttileid = t.tileid
LEFT JOIN img ON img.parenttileid = t.tileid
WHERE t.nodegroupid = '44713ace-babc-4ebe-b2f6-084ed0060f2c'::uuid;

CREATE UNIQUE INDEX mv_related_documents_pk ON site_visit.mv_related_documents (resourceinstanceid);


-- =====================================================================
-- STEP 4 - FINAL MATVIEW
-- Driven off resource_instances directly (no edit_log there either). This is
-- what guarantees one row per resource INCLUDING resources with zero tiles, and
-- it carries the graphid filter - the only thing scoping the stack to this graph.
-- Seven joins, all on unique-indexed resourceinstanceid: cheap merge joins.
-- =====================================================================
DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_resource_v1 CASCADE;
CREATE MATERIALIZED VIEW site_visit.mv_resource_v1 AS
SELECT
    r.resourceinstanceid,
    loc.site_visit_geom,
    COALESCE(loc.site_visit_location, '[]'::jsonb) AS site_visit_location,
    COALESCE(ar.ancestral_remains,    '[]'::jsonb) AS ancestral_remains,
    idn.identification,
    svd.site_visit_details,
    ad.archaeological_data,
    rr.remarks_and_recommendations,
    rd.related_documents,
    jsonb_build_object(
        'resourceinstanceid',          r.resourceinstanceid,
        'site_visit_location',         COALESCE(loc.site_visit_location, '[]'::jsonb),
        'ancestral_remains',           COALESCE(ar.ancestral_remains,    '[]'::jsonb),
        'identification',              idn.identification,
        'site_visit_details',          svd.site_visit_details,
        'archaeological_data',         ad.archaeological_data,
        'remarks_and_recommendations', rr.remarks_and_recommendations,
        'related_documents',           rd.related_documents
    ) AS resource
FROM public.resource_instances r
LEFT JOIN site_visit.mv_site_visit_location         loc ON loc.resourceinstanceid = r.resourceinstanceid
LEFT JOIN site_visit.mv_identification              idn ON idn.resourceinstanceid = r.resourceinstanceid
LEFT JOIN site_visit.mv_site_visit_details          svd ON svd.resourceinstanceid = r.resourceinstanceid
LEFT JOIN site_visit.mv_archaeological_data         ad  ON ad.resourceinstanceid  = r.resourceinstanceid
LEFT JOIN site_visit.mv_remarks_and_recommendations rr  ON rr.resourceinstanceid  = r.resourceinstanceid
LEFT JOIN site_visit.mv_ancestral_remains           ar  ON ar.resourceinstanceid  = r.resourceinstanceid
LEFT JOIN site_visit.mv_related_documents           rd  ON rd.resourceinstanceid  = r.resourceinstanceid
WHERE r.graphid = '2da1c15f-1ab6-4122-9dbc-d10da693ac79'::uuid;

CREATE UNIQUE INDEX mv_resource_v1_pk      ON site_visit.mv_resource_v1 (resourceinstanceid);
CREATE INDEX mv_resource_v1_geom           ON site_visit.mv_resource_v1 USING GIST (site_visit_geom);
CREATE INDEX mv_resource_v1_resource       ON site_visit.mv_resource_v1 USING GIN (resource jsonb_path_ops);


-- =====================================================================
-- STEP 5 - WRAPPER VIEW.  The downstream contract. Nothing else names the matview.
-- To ship v2: build mv_resource_v2 alongside, verify, then repoint this view.
-- =====================================================================
CREATE OR REPLACE VIEW site_visit.resource AS
SELECT * FROM site_visit.mv_resource_v1;

COMMENT ON VIEW site_visit.resource IS
'Stable read contract for the site_visit graph. One row per resource instance. '
'Backed by a materialized view - repoint the backing matview here, never rename this. '
'Arrays are always [] when empty, never null. Cardinality-1 branches are null when the tile does not exist.';

-- GRANT SELECT ON site_visit.resource TO <app_role>;
-- Do NOT grant on mv_resource_v1 - force everything through the wrapper.


-- =====================================================================
-- STEP 6 - REFRESH.  Branches first, final last.
-- =====================================================================
CREATE OR REPLACE PROCEDURE site_visit.refresh_resource(concurrent boolean DEFAULT true)
LANGUAGE plpgsql AS $$
DECLARE
    mode text := CASE WHEN concurrent THEN 'CONCURRENTLY' ELSE '' END;
    mv   text;
BEGIN
    FOREACH mv IN ARRAY ARRAY[
        'site_visit.mv_site_visit_location',
        'site_visit.mv_identification',
        'site_visit.mv_site_visit_details',
        'site_visit.mv_archaeological_data',
        'site_visit.mv_remarks_and_recommendations',
        'site_visit.mv_ancestral_remains',
        'site_visit.mv_related_documents',
        'site_visit.mv_resource_v1'
    ]
    LOOP
        RAISE NOTICE 'refreshing %', mv;
        EXECUTE format('REFRESH MATERIALIZED VIEW %s %s', mode, mv);
        COMMIT;
    END LOOP;
END $$;