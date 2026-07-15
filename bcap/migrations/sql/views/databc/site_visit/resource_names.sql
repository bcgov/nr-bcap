-- =====================================================================
--  RESOURCE-INSTANCE NAME RESOLUTION
--  Prepend this to site_visit_flat.sql (it defines what the flat view calls).
--
--  WHY NOT THE JOIN YOU PROPOSED
--  ---------------------------------------------------------------------
--      join resource_instances aff ON uuid(r.site_visit_details ->> 'affiliation')
--                                   = aff.resourceinstanceid
--
--  1. It is an INNER join. Every site visit with no affiliation is DROPPED.
--     There are TEN resource-instance columns; chaining ten inner joins would
--     leave only the rows that happen to populate all ten. Silently. No error.
--
--  2. uuid('') RAISES. One malformed value anywhere in those ten columns aborts
--     the REFRESH and takes site_visit.resource_flat down with it.
--     arches_util.to_uuid() below returns NULL instead of exploding.
--
--  3. It only reaches 3 of the 10 columns. affiliation, archaeological_site and
--     temporary_number_assigned_by are single values on cardinality-1 objects.
--     The rest are uuid CSVs (one per tile) or LISTS of uuids per tile. No
--     equality join gets at those - they need mapping, not joining.
--
--  4. resource_instances.name is (almost certainly) jsonb i18n, so aff.name
--     would hand you {"en": {"value": "..."}} rather than a name.
--     RUN THIS FIRST:
--         SELECT pg_typeof(name), name, descriptors FROM resource_instances LIMIT 3;
--     The lookup below handles BOTH shapes without branching - to_jsonb() turns a
--     text name into a JSON string, and i18n_text() already has a 'string' branch
--     that passes it straight through - but confirm rather than assume.
-- =====================================================================


-- ---------------------------------------------------------------------
-- Safe uuid cast. Regex-guarded rather than an exception block: a plpgsql
-- EXCEPTION opens a subtransaction PER ROW, which is brutal at this width.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION arches_util.to_uuid(t text)
RETURNS uuid LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN t ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        THEN t::uuid
    END;
$$;


-- ---------------------------------------------------------------------
-- Name lookup for EVERY resource in the database, not just site visits - these
-- references point at Permits, Persons, Archaeological Sites, Repositories, all
-- different graphs.
--
-- Materialized, and the UNIQUE INDEX is NOT optional: resource_name() below does
-- a point lookup per call, and this table is read once per resource-instance
-- value in a 131-column table. Without the index every call is a seq scan and the
-- refresh becomes O(N*M). With it, each is a btree probe.
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS arches_util.mv_resource_name CASCADE;
CREATE MATERIALIZED VIEW arches_util.mv_resource_name AS
SELECT ri.resourceinstanceid,
       COALESCE(
           -- to_jsonb() makes this work whether `name` is jsonb i18n or plain text
           arches_util.i18n_text(to_jsonb(ri.name)),
           ri.descriptors -> 'en' ->> 'name',
           (SELECT d.value ->> 'name'
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


-- ---------------------------------------------------------------------
-- Three mapping shapes, matching the three ways a resource reference appears.
-- All preserve empty slots, same as a2csv - a tile with no reference still emits
-- its slot, so these columns stay positionally aligned with their siblings.
-- A DANGLING reference (points at a deleted resource) resolves to an empty slot,
-- NOT a dropped one. Query D below finds them.
-- ---------------------------------------------------------------------

-- val is a jsonb ARRAY OF UUID STRINGS  (resource-instance-list on a card-1 object:
-- associated_permit, site_form_authors)
CREATE OR REPLACE FUNCTION arches_util.resource_names_csv(val jsonb, delim text DEFAULT ' | ')
RETURNS text LANGUAGE sql STABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN jsonb_typeof(val) <> 'array' THEN NULL
        WHEN jsonb_array_length(val) = 0  THEN NULL
        ELSE (
            SELECT string_agg(
                replace(COALESCE(
                    arches_util.resource_name(arches_util.to_uuid(e.item #>> '{}')), ''),
                    '|', '/'),
                delim ORDER BY e.ord)
            FROM jsonb_array_elements(val) WITH ORDINALITY AS e(item, ord))
    END;
$$;

-- arr is an array of TILE objects; arr[i]->>key is a SINGLE uuid string
-- (repository, team_member, assigned_or_reported_by, ancestral_remains_repository)
CREATE OR REPLACE FUNCTION arches_util.resource_name_col(
    arr jsonb, key text, delim text DEFAULT ' | ')
RETURNS text LANGUAGE sql STABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN jsonb_typeof(arr) <> 'array' THEN NULL
        WHEN jsonb_array_length(arr) = 0  THEN NULL
        ELSE (
            SELECT string_agg(
                replace(COALESCE(
                    arches_util.resource_name(arches_util.to_uuid(e.item ->> key)), ''),
                    '|', '/'),
                delim ORDER BY e.ord)
            FROM jsonb_array_elements(arr) WITH ORDINALITY AS e(item, ord))
    END;
$$;

-- arr is an array of TILE objects; arr[i]->key is an ARRAY of uuid strings
-- (publication_reference)
CREATE OR REPLACE FUNCTION arches_util.resource_names_nested(
    arr jsonb, key text, delim text DEFAULT ' | ', inner_delim text DEFAULT '; ')
RETURNS text LANGUAGE sql STABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN jsonb_typeof(arr) <> 'array' THEN NULL
        WHEN jsonb_array_length(arr) = 0  THEN NULL
        ELSE (
            SELECT string_agg(
                COALESCE(arches_util.resource_names_csv(e.item -> key, inner_delim), ''),
                delim ORDER BY e.ord)
            FROM jsonb_array_elements(arr) WITH ORDINALITY AS e(item, ord))
    END;
$$;


-- =====================================================================
-- REFRESH ORDER  -- mv_resource_name must be FRESH before the flat view reads it.
-- It is independent of the branch matviews, so it can go first.
--
--   arches_util.mv_resource_name
--   -> 7 branch matviews
--   -> site_visit.mv_resource_v1
--   -> site_visit.mv_resource_flat_v1
--
-- A STALE mv_resource_name does not error - it just resolves a renamed resource
-- to its old name, or a brand-new one to NULL. Silent. Refresh it every cycle.
-- =====================================================================
CREATE OR REPLACE PROCEDURE arches_util.refresh_resource_name(concurrent boolean DEFAULT true)
LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE format('REFRESH MATERIALIZED VIEW %s arches_util.mv_resource_name',
                   CASE WHEN concurrent THEN 'CONCURRENTLY' ELSE '' END);
END $$;


-- =====================================================================
-- D. DANGLING REFERENCE CHECK.  Run after the first build.
--
-- A reference pointing at a deleted resource resolves to an EMPTY SLOT - the row
-- survives (unlike with your inner join), the position is preserved, but the name
-- is blank. That is the correct behaviour, and it is also invisible unless you
-- look. This finds them.
--
-- Expect 0. Non-zero means either genuine referential rot in the tiles, or a
-- resource that exists but has no resolvable name (check the probe above).
-- =====================================================================
WITH refs AS (
    SELECT 'affiliation' AS col, arches_util.to_uuid(site_visit_details ->> 'affiliation') AS id
    FROM site_visit.mv_resource_v1
    UNION ALL
    SELECT 'archaeological_site', arches_util.to_uuid(site_visit_details ->> 'archaeological_site')
    FROM site_visit.mv_resource_v1
    UNION ALL
    SELECT 'associated_permit', arches_util.to_uuid(e #>> '{}')
    FROM site_visit.mv_resource_v1,
         LATERAL jsonb_array_elements(arches_util.as_array(site_visit_details -> 'associated_permit')) e
    UNION ALL
    SELECT 'site_form_authors', arches_util.to_uuid(e #>> '{}')
    FROM site_visit.mv_resource_v1,
         LATERAL jsonb_array_elements(arches_util.as_array(site_visit_details -> 'site_form_authors')) e
    UNION ALL
    SELECT 'team_member', arches_util.to_uuid(e ->> 'team_member')
    FROM site_visit.mv_resource_v1,
         LATERAL jsonb_array_elements(arches_util.as_array(
             site_visit_details -> 'site_visit_team' -> 'team_member')) e
    UNION ALL
    SELECT 'repository', arches_util.to_uuid(e ->> 'repository')
    FROM site_visit.mv_resource_v1,
         LATERAL jsonb_array_elements(arches_util.as_array(archaeological_data -> 'cultural_material')) e
    UNION ALL
    SELECT 'assigned_or_reported_by', arches_util.to_uuid(e ->> 'assigned_or_reported_by')
    FROM site_visit.mv_resource_v1,
         LATERAL jsonb_array_elements(arches_util.as_array(identification -> 'new_site_names')) e
    UNION ALL
    SELECT 'ancestral_remains_repository', arches_util.to_uuid(e ->> 'ancestral_remains_repository')
    FROM site_visit.mv_resource_v1,
         LATERAL jsonb_array_elements(arches_util.as_array(ancestral_remains)) e
    UNION ALL
    SELECT 'temporary_number_assigned_by',
           arches_util.to_uuid(identification -> 'temporary_number' ->> 'temporary_number_assigned_by')
    FROM site_visit.mv_resource_v1
    UNION ALL
    SELECT 'publication_reference', arches_util.to_uuid(i #>> '{}')
    FROM site_visit.mv_resource_v1,
         LATERAL jsonb_array_elements(arches_util.as_array(related_documents -> 'publication_reference')) e,
         LATERAL jsonb_array_elements(arches_util.as_array(e -> 'publication_reference')) i
)
SELECT refs.col,
       count(*)                                         AS total_refs,
       count(*) FILTER (WHERE n.resourceinstanceid IS NULL) AS dangling,
       count(*) FILTER (WHERE n.resourceinstanceid IS NOT NULL
                          AND n.name IS NULL)           AS exists_but_unnamed
FROM refs
LEFT JOIN arches_util.mv_resource_name n ON n.resourceinstanceid = refs.id
WHERE refs.id IS NOT NULL
GROUP BY refs.col
ORDER BY dangling DESC, refs.col;