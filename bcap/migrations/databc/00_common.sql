-- =====================================================================
--  00_common.sql  --  arches_util
--  Shared by EVERY resource model. Apply this first, once.
--
--  Nothing in here is graph-specific. The per-graph files (sv_*, as_*) are
--  generated and depend on these functions existing.
--
--  APPLY ORDER
--    1. 00_common.sql                 <- this file
--    2. <slug>_01_preflight.sql       <- read the results before going further
--    3. <slug>_02_stack.sql           <- nested jsonb object + wrapper view
--    4. <slug>_03_flat.sql            <- denormalized tables + alignment test
--
--  REFRESH ORDER (mv_resource_name FIRST - a stale one does not error, it just
--  resolves a renamed resource to its OLD name, silently):
--    CALL arches_util.refresh_resource_name();
--    CALL site_visit.refresh_resource();          CALL site_visit.refresh_flat();
--    CALL archaeological_site.refresh_resource(); CALL archaeological_site.refresh_flat();
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS arches_util;


-- =====================================================================
-- 0. SUPPORTING INDEXES ON CORE ARCHES TABLES
--    These index the join columns used throughout the materialized views.
--    Safe to re-apply (IF NOT EXISTS).
-- =====================================================================
CREATE INDEX IF NOT EXISTS tiles_nodegroupid_idx
    ON public.tiles (nodegroupid);
CREATE INDEX IF NOT EXISTS geojson_geometries_nodeid_idx
    ON public.geojson_geometries (nodeid);
CREATE INDEX IF NOT EXISTS resource_instances_graphid_idx
    ON public.resource_instances (graphid);


-- =====================================================================
-- 1. VALUE DECODING  (tiledata jsonb -> usable values)
-- =====================================================================

-- Coerce anything that is not a jsonb array into an empty array, so the
-- set-returning functions below cannot raise "cannot extract elements from a
-- scalar" on a stray JSON null.
CREATE OR REPLACE FUNCTION arches_util.as_array(val jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE WHEN jsonb_typeof(val) = 'array' THEN val ELSE '[]'::jsonb END;
$$;


-- THERE ARE TWO DIFFERENT i18n SHAPES IN THIS DATABASE:
--
--   tiles.tiledata           {"en": {"value": "some text", "direction": "ltr"}}
--   resource_instances.name  {"en": "ElSw-43 (Discontinued)"}
--
-- i.e. the language key maps to an OBJECT in one and to a BARE STRING in the
-- other. A resolver that only handles the first returns NULL for every resource
-- name - which is exactly what happened, and went unnoticed because
-- mv_resource_name coalesced to descriptors as a "fallback" that was in fact
-- carrying the whole thing.
CREATE OR REPLACE FUNCTION arches_util.i18n_leaf(v jsonb)
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE jsonb_typeof(v)
        WHEN 'object' THEN v ->> 'value'   -- tiledata
        WHEN 'string' THEN v #>> '{}'      -- resource_instances.name
        ELSE NULL
    END;
$$;

CREATE OR REPLACE FUNCTION arches_util.i18n_text(val jsonb, lang text DEFAULT 'en')
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE RETURNS NULL ON NULL INPUT AS $$
    SELECT CASE jsonb_typeof(val)
        WHEN 'string' THEN val #>> '{}'
        WHEN 'object' THEN COALESCE(
            NULLIF(arches_util.i18n_leaf(val -> lang), ''),
            (SELECT NULLIF(arches_util.i18n_leaf(e.v), '')
               FROM jsonb_each(val) AS e(k, v)
              WHERE NULLIF(arches_util.i18n_leaf(e.v), '') IS NOT NULL
              ORDER BY e.k LIMIT 1))
        ELSE NULL
    END;
$$;


-- reference (controlled list) -> [{"list_item_id": uuid, "label": text}, ...]
--
-- The item id lives at labels[].list_item_id. An item carries SEVERAL labels
-- (prefLabel, altLabel, scopeNote, definition, ...), so the label lookup filters
-- on valuetype_id and deliberately STOPS at altLabel. It never falls through to a
-- note: a NULL label is a visible failure, a definition paragraph masquerading as
-- a display label is an invisible one.
--
-- `uri` and `list_id` are both DROPPED. The uri carries an environment host in
-- some tiles and not others ("http://localhost:82/..." vs "/bcap/..."), and
-- neither belongs in a contract downstream apps depend on. Fallback for
-- label-less values parses the trailing uuid off the uri path, which is
-- host-independent.
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
                (SELECT l ->> 'value' FROM jsonb_array_elements(arches_util.as_array(item -> 'labels')) l
                  WHERE l ->> 'valuetype_id' = 'prefLabel' AND l ->> 'language_id' = lang LIMIT 1),
                (SELECT l ->> 'value' FROM jsonb_array_elements(arches_util.as_array(item -> 'labels')) l
                  WHERE l ->> 'valuetype_id' = 'prefLabel' LIMIT 1),
                (SELECT l ->> 'value' FROM jsonb_array_elements(arches_util.as_array(item -> 'labels')) l
                  WHERE l ->> 'valuetype_id' = 'altLabel' AND l ->> 'language_id' = lang LIMIT 1),
                (SELECT l ->> 'value' FROM jsonb_array_elements(arches_util.as_array(item -> 'labels')) l
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

-- Returned as TEXT, not UUID, on purpose: one malformed id would abort the whole
-- REFRESH and take the downstream wrapper view with it.
CREATE OR REPLACE FUNCTION arches_util.resource_id(val jsonb)
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE RETURNS NULL ON NULL INPUT AS $$
    SELECT CASE WHEN jsonb_typeof(val) <> 'array' THEN NULL
           ELSE (val -> 0) ->> 'resourceId' END;
$$;


-- file-list.
--   DROPPED - `content`: a blob: URL with the environment host baked in
--     ("blob:https://bcapapps.nrs.gov.bc.ca/bcap/<uuid>"). Meaningless
--     server-side, dead the moment the session that minted it ended, and it
--     hardcodes the environment. The single worst field to put in a contract.
--   DROPPED - `accepted`: transient client-side upload state, not data.
--   FLATTENED - title / altText / attribution / description are i18n OBJECTS.
--     alt_text matters for accessibility and attribution for copyright.
--   `index` is the author's intended ordering; used as the sort key.
--   `lastModified` is epoch MILLIseconds, emitted as an explicit UTC ISO string:
--     to_json(timestamptz) formats in the session TimeZone, and a contract must
--     not move when someone changes a session setting.
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


-- Arches `url` datatype -> {"url": ..., "label": ..., "raw": ...}
-- Confirmed shape: {"url": "https://...", "url_label": "..."} with url_label a
-- PLAIN string. Falls back to a bare string, and if the value is NEITHER shape it
-- stashes the original under 'raw' rather than dropping it - so an unanticipated
-- shape shows up in the CI check below instead of silently becoming NULL.
CREATE OR REPLACE FUNCTION arches_util.url_obj(val jsonb, lang text DEFAULT 'en')
RETURNS jsonb LANGUAGE sql IMMUTABLE PARALLEL SAFE RETURNS NULL ON NULL INPUT AS $$
    SELECT CASE
        WHEN jsonb_typeof(val) = 'object' AND val ? 'url' THEN
            jsonb_build_object('url', val ->> 'url',
                'label', COALESCE(arches_util.i18n_text(val -> 'url_label', lang),
                                  val ->> 'url_label'),
                'raw', NULL)
        WHEN jsonb_typeof(val) = 'string' THEN
            jsonb_build_object('url', val #>> '{}', 'label', NULL, 'raw', NULL)
        WHEN jsonb_typeof(val) = 'null' THEN
            jsonb_build_object('url', NULL, 'label', NULL, 'raw', NULL)
        ELSE
            jsonb_build_object('url', NULL, 'label', NULL, 'raw', val)
    END;
$$;


-- =====================================================================
-- 2. RESOURCE NAME RESOLUTION
-- =====================================================================

-- Regex-guarded rather than an exception block: a plpgsql EXCEPTION opens a
-- SUBTRANSACTION PER ROW, which is brutal across a 120-column table. And a bare
-- uuid('') RAISES, which would abort the refresh.
CREATE OR REPLACE FUNCTION arches_util.to_uuid(t text)
RETURNS uuid LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE WHEN t ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                THEN t::uuid END;
$$;

-- Names for EVERY resource, not just one graph - these references point at
-- Permits, Persons, Archaeological Sites, Repositories, across graphs.
-- The UNIQUE INDEX is NOT optional: resource_name() does a point lookup per call,
-- once per resource-instance value in a wide table. Without it every call is a
-- seq scan and the refresh goes O(N*M).
DROP MATERIALIZED VIEW IF EXISTS arches_util.mv_resource_name CASCADE;
CREATE MATERIALIZED VIEW arches_util.mv_resource_name AS
SELECT ri.resourceinstanceid,
       COALESCE(
           arches_util.i18n_text(to_jsonb(ri.name)),
           NULLIF(ri.descriptors -> 'en' ->> 'name', ''),
           (SELECT NULLIF(d.value ->> 'name', '')
              FROM jsonb_each(ri.descriptors) d
             WHERE NULLIF(d.value ->> 'name', '') IS NOT NULL
             ORDER BY d.key LIMIT 1)
       ) AS name,
       ri.graphid
FROM public.resource_instances ri;

CREATE UNIQUE INDEX mv_resource_name_pk ON arches_util.mv_resource_name (resourceinstanceid);

CREATE OR REPLACE FUNCTION arches_util.resource_name(id uuid)
RETURNS text LANGUAGE sql STABLE PARALLEL SAFE RETURNS NULL ON NULL INPUT AS $$
    SELECT n.name FROM arches_util.mv_resource_name n WHERE n.resourceinstanceid = id;
$$;

CREATE OR REPLACE PROCEDURE arches_util.refresh_resource_name(concurrent boolean DEFAULT true)
LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE format('REFRESH MATERIALIZED VIEW %s arches_util.mv_resource_name',
                   CASE WHEN concurrent THEN 'CONCURRENTLY' ELSE '' END);
END $$;


-- =====================================================================
-- 3. CSV FLATTENING  (for the flat layer)
--
--  EVERY function here walks EVERY element of the array and COALESCEs missing
--  values to '', so it emits exactly ONE SLOT PER TILE. That is the entire basis
--  of positional alignment between sibling columns. Do not "tidy up" the empty
--  slots - "a |  | c" means the middle tile was empty, and a reader relies on it.
--
--  Delimiters: ' | ' between tiles, '; ' within one tile. NOT a comma - the
--  free-text fields are full of commas. A literal '|' in source text is replaced
--  with '/' so it cannot collide.
-- =====================================================================

CREATE OR REPLACE FUNCTION arches_util.a2csv(
    val jsonb, field text DEFAULT NULL, delim text DEFAULT ' | ')
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN jsonb_typeof(val) <> 'array' THEN NULL
        WHEN jsonb_array_length(val) = 0  THEN NULL
        ELSE (SELECT string_agg(
                replace(COALESCE(CASE WHEN field IS NULL THEN e.item #>> '{}'
                                      ELSE e.item ->> field END, ''), '|', '/'),
                delim ORDER BY e.ord)
              FROM jsonb_array_elements(val) WITH ORDINALITY AS e(item, ord))
    END;
$$;

-- `path` is the object path from an array ELEMENT down to the nodegroup owning
-- the field. e.g. site_tenure_type lives at
--     site_location[i] -> 'site_tenure' -> 'site_tenure_type'
-- so path = '{site_tenure,site_tenure_type}'. Empty path = field is on the element.

CREATE OR REPLACE FUNCTION arches_util.deep_csv(
    arr jsonb, path text[], field text, delim text DEFAULT ' | ')
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN jsonb_typeof(arr) <> 'array' THEN NULL
        WHEN jsonb_array_length(arr) = 0  THEN NULL
        ELSE (SELECT string_agg(
                replace(COALESCE((e.item #> path) ->> field, ''), '|', '/'),
                delim ORDER BY e.ord)
              FROM jsonb_array_elements(arr) WITH ORDINALITY AS e(item, ord))
    END;
$$;

-- field is an ARRAY of objects (reference / file-list) -> pluck subfield
CREATE OR REPLACE FUNCTION arches_util.deep_csv_nested(
    arr jsonb, path text[], field text, subfield text,
    delim text DEFAULT ' | ', inner_delim text DEFAULT '; ')
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN jsonb_typeof(arr) <> 'array' THEN NULL
        WHEN jsonb_array_length(arr) = 0  THEN NULL
        ELSE (SELECT string_agg(
                COALESCE(arches_util.a2csv((e.item #> path) -> field, subfield, inner_delim), ''),
                delim ORDER BY e.ord)
              FROM jsonb_array_elements(arr) WITH ORDINALITY AS e(item, ord))
    END;
$$;

-- field is an OBJECT -> pluck a key from it
CREATE OR REPLACE FUNCTION arches_util.deep_csv_sub(
    arr jsonb, path text[], field text, subkey text, delim text DEFAULT ' | ')
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN jsonb_typeof(arr) <> 'array' THEN NULL
        WHEN jsonb_array_length(arr) = 0  THEN NULL
        ELSE (SELECT string_agg(
                replace(COALESCE(((e.item #> path) -> field) ->> subkey, ''), '|', '/'),
                delim ORDER BY e.ord)
              FROM jsonb_array_elements(arr) WITH ORDINALITY AS e(item, ord))
    END;
$$;

-- URL-safe variant. The generic helpers replace a literal '|' with '/'. For free
-- text that is cosmetic; for a URL it is CORRUPTION:
--     https://a.example/x?a=1|b=2  ->  https://a.example/x?a=1/b=2   (different URL)
-- %7C is the correct percent-encoding: it cannot collide with the delimiter AND
-- the URL still resolves. Labels keep the '/' substitution - they are display text.
CREATE OR REPLACE FUNCTION arches_util.deep_url_csv(
    arr jsonb, path text[], field text, delim text DEFAULT ' | ')
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN jsonb_typeof(arr) <> 'array' THEN NULL
        WHEN jsonb_array_length(arr) = 0  THEN NULL
        ELSE (SELECT string_agg(
                replace(COALESCE(((e.item #> path) -> field) ->> 'url', ''), '|', '%7C'),
                delim ORDER BY e.ord)
              FROM jsonb_array_elements(arr) WITH ORDINALITY AS e(item, ord))
    END;
$$;

-- single resource-instance uuid -> resolved name
CREATE OR REPLACE FUNCTION arches_util.deep_res_csv(
    arr jsonb, path text[], field text, delim text DEFAULT ' | ')
RETURNS text LANGUAGE sql STABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN jsonb_typeof(arr) <> 'array' THEN NULL
        WHEN jsonb_array_length(arr) = 0  THEN NULL
        ELSE (SELECT string_agg(
                replace(COALESCE(arches_util.resource_name(
                    arches_util.to_uuid((e.item #> path) ->> field)), ''), '|', '/'),
                delim ORDER BY e.ord)
              FROM jsonb_array_elements(arr) WITH ORDINALITY AS e(item, ord))
    END;
$$;

CREATE OR REPLACE FUNCTION arches_util.resource_names_csv(val jsonb, delim text DEFAULT ' | ')
RETURNS text LANGUAGE sql STABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN jsonb_typeof(val) <> 'array' THEN NULL
        WHEN jsonb_array_length(val) = 0  THEN NULL
        ELSE (SELECT string_agg(
                replace(COALESCE(arches_util.resource_name(
                    arches_util.to_uuid(e.item #>> '{}')), ''), '|', '/'),
                delim ORDER BY e.ord)
              FROM jsonb_array_elements(val) WITH ORDINALITY AS e(item, ord))
    END;
$$;

-- resource-instance-LIST inside each tile
CREATE OR REPLACE FUNCTION arches_util.deep_res_csv_nested(
    arr jsonb, path text[], field text,
    delim text DEFAULT ' | ', inner_delim text DEFAULT '; ')
RETURNS text LANGUAGE sql STABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN jsonb_typeof(arr) <> 'array' THEN NULL
        WHEN jsonb_array_length(arr) = 0  THEN NULL
        ELSE (SELECT string_agg(
                COALESCE(arches_util.resource_names_csv((e.item #> path) -> field, inner_delim), ''),
                delim ORDER BY e.ord)
              FROM jsonb_array_elements(arr) WITH ORDINALITY AS e(item, ord))
    END;
$$;

-- Slot counter for the alignment test. Counts DELIMITERS - it must not use
-- string_to_array, because array_length(string_to_array('', ' | '), 1) is NULL,
-- not 1, and a single-tile group with an empty field would then be flagged as
-- misaligned. That produced thousands of false positives before it was caught.
CREATE OR REPLACE FUNCTION arches_util.nslots(s text, delim text DEFAULT ' | ')
RETURNS int LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE WHEN s IS NULL THEN 0
           ELSE (length(s) - length(replace(s, delim, ''))) / length(delim) + 1 END;
$$;
