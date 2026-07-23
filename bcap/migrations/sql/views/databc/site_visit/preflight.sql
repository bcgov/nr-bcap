-- =====================================================================
--  site_visit :: PREFLIGHT
--  Run every check in this file BEFORE running site_visit_mv_stack.sql.
--
--  Ordered by blast radius. A, B and C can change the DDL. D-H change your
--  expectations or your rollout, not the code. Each says what to do with the
--  result - none of them are "run it and squint at the output".
-- =====================================================================


-- =====================================================================
-- A. CARDINALITY.  THE LOAD-BEARING ASSUMPTION.  Run this one first.
-- ---------------------------------------------------------------------
-- Every array-vs-object decision in the stack came from reading your resource
-- tree JSON: arrays -> cardinality n, objects -> cardinality 1. That is an
-- inference from ONE sample resource. If any nodegroup I read as "1" is really
-- "n", the unique index on that branch matview will abort the refresh - loudly,
-- which is the good outcome - but you would rather know now than at 3am.
--
-- Expected, from the tree:
--   n : site_visit_location, biogeography, ancestral_remains, new_site_names,
--       team_member, cultural_material, stratigraphy, archaeological_feature,
--       chronology, archaeological_culture, site_disturbance,
--       additional_site_typology, recommendation, general_remark,
--       related_site_documents, publication_reference, site_images
--   1 : identification, temporary_number, site_visit_details, site_visit_team,
--       archaeological_data, remarks_and_recommendations, related_documents
--
-- ANY disagreement -> fix the stack before building, do not "try it and see".
SELECT n.name                     AS view_name,
       ng.cardinality,
       pn.name                    AS parent_view,
       ng.nodegroupid
FROM node_groups ng
JOIN nodes n              ON n.nodeid = ng.nodegroupid
LEFT JOIN node_groups png ON png.nodegroupid = ng.parentnodegroupid
LEFT JOIN nodes pn        ON pn.nodeid = png.nodegroupid
WHERE n.graphid = '2da1c15f-1ab6-4122-9dbc-d10da693ac79'
ORDER BY COALESCE(pn.name, ''), n.name;


-- =====================================================================
-- B. ORPHAN CHILD TILES.  Silent data loss if non-zero.
-- ---------------------------------------------------------------------
-- Every branch matview drives off the PARENT tile and LEFT JOINs the children.
-- A child tile whose parenttileid points at a parent that is not in the parent
-- view - deleted parent, or a parent knocked out by the edit_log anti-join -
-- simply VANISHES from the output. No error, no constraint, no clue.
--
-- Expect 0 everywhere. Non-zero means either genuinely orphaned tiles in the
-- DB (a data problem worth fixing at the source) or a bug in the source views.
-- Either way, do not build on top of it.
-- Table names cannot be parameterised in plain SQL, so this generates the 17
-- statements. Run it, copy the output, run that. Every line must return 0 / 0.
SELECT format(
    'SELECT %L AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.%I IS NOT NULL) AS orphans, '
    'count(*) FILTER (WHERE c.%I IS NULL) AS null_parents '
    'FROM site_visit.%I c LEFT JOIN site_visit.%I p ON p.tileid = c.%I',
    child_view, parent_col, parent_col, child_view, parent_view, parent_col)
FROM (VALUES
    ('biogeography',             'site_visit_location',         'site_visit_location'),
    ('new_site_names',           'identification',              'identification'),
    ('temporary_number',         'identification',              'identification'),
    ('site_visit_team',          'site_visit_details',          'site_visit_details'),
    ('team_member',              'site_visit_team',             'site_visit_team'),
    ('cultural_material',        'archaeological_data',         'archaeological_data'),
    ('stratigraphy',             'archaeological_data',         'archaeological_data'),
    ('archaeological_feature',   'archaeological_data',         'archaeological_data'),
    ('chronology',               'archaeological_data',         'archaeological_data'),
    ('archaeological_culture',   'archaeological_data',         'archaeological_data'),
    ('site_disturbance',         'archaeological_data',         'archaeological_data'),
    ('additional_site_typology', 'archaeological_data',         'archaeological_data'),
    ('recommendation',           'remarks_and_recommendations', 'remarks_and_recommendations'),
    ('general_remark',           'remarks_and_recommendations', 'remarks_and_recommendations'),
    ('related_site_documents',   'related_documents',           'related_documents'),
    ('publication_reference',    'related_documents',           'related_documents'),
    ('site_images',              'related_documents',           'related_documents')
) AS t(child_view, parent_col, parent_view);
-- Copy the 17 generated statements out, run them, expect 0 / 0 on every line.
SELECT 'biogeography' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.site_visit_location IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.site_visit_location IS NULL) AS null_parents FROM site_visit.biogeography c LEFT JOIN site_visit.site_visit_location p ON p.tileid = c.site_visit_location
SELECT 'new_site_names' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.identification IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.identification IS NULL) AS null_parents FROM site_visit.new_site_names c LEFT JOIN site_visit.identification p ON p.tileid = c.identification
SELECT 'temporary_number' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.identification IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.identification IS NULL) AS null_parents FROM site_visit.temporary_number c LEFT JOIN site_visit.identification p ON p.tileid = c.identification
SELECT 'site_visit_team' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.site_visit_details IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.site_visit_details IS NULL) AS null_parents FROM site_visit.site_visit_team c LEFT JOIN site_visit.site_visit_details p ON p.tileid = c.site_visit_details
SELECT 'team_member' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.site_visit_team IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.site_visit_team IS NULL) AS null_parents FROM site_visit.team_member c LEFT JOIN site_visit.site_visit_team p ON p.tileid = c.site_visit_team
SELECT 'cultural_material' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.archaeological_data IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.archaeological_data IS NULL) AS null_parents FROM site_visit.cultural_material c LEFT JOIN site_visit.archaeological_data p ON p.tileid = c.archaeological_data
SELECT 'stratigraphy' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.archaeological_data IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.archaeological_data IS NULL) AS null_parents FROM site_visit.stratigraphy c LEFT JOIN site_visit.archaeological_data p ON p.tileid = c.archaeological_data
SELECT 'archaeological_feature' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.archaeological_data IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.archaeological_data IS NULL) AS null_parents FROM site_visit.archaeological_feature c LEFT JOIN site_visit.archaeological_data p ON p.tileid = c.archaeological_data
SELECT 'chronology' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.archaeological_data IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.archaeological_data IS NULL) AS null_parents FROM site_visit.chronology c LEFT JOIN site_visit.archaeological_data p ON p.tileid = c.archaeological_data
SELECT 'archaeological_culture' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.archaeological_data IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.archaeological_data IS NULL) AS null_parents FROM site_visit.archaeological_culture c LEFT JOIN site_visit.archaeological_data p ON p.tileid = c.archaeological_data
SELECT 'site_disturbance' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.archaeological_data IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.archaeological_data IS NULL) AS null_parents FROM site_visit.site_disturbance c LEFT JOIN site_visit.archaeological_data p ON p.tileid = c.archaeological_data
SELECT 'additional_site_typology' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.archaeological_data IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.archaeological_data IS NULL) AS null_parents FROM site_visit.additional_site_typology c LEFT JOIN site_visit.archaeological_data p ON p.tileid = c.archaeological_data
SELECT 'recommendation' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.remarks_and_recommendations IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.remarks_and_recommendations IS NULL) AS null_parents FROM site_visit.recommendation c LEFT JOIN site_visit.remarks_and_recommendations p ON p.tileid = c.remarks_and_recommendations
SELECT 'general_remark' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.remarks_and_recommendations IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.remarks_and_recommendations IS NULL) AS null_parents FROM site_visit.general_remark c LEFT JOIN site_visit.remarks_and_recommendations p ON p.tileid = c.remarks_and_recommendations
SELECT 'related_site_documents' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.related_documents IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.related_documents IS NULL) AS null_parents FROM site_visit.related_site_documents c LEFT JOIN site_visit.related_documents p ON p.tileid = c.related_documents
SELECT 'publication_reference' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.related_documents IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.related_documents IS NULL) AS null_parents FROM site_visit.publication_reference c LEFT JOIN site_visit.related_documents p ON p.tileid = c.related_documents
SELECT 'site_images' AS child_view, count(*) FILTER (WHERE p.tileid IS NULL AND c.related_documents IS NOT NULL) AS orphans, count(*) FILTER (WHERE c.related_documents IS NULL) AS null_parents FROM site_visit.site_images c LEFT JOIN site_visit.related_documents p ON p.tileid = c.related_documents


-- =====================================================================
-- C. GEOMETRY.  This one can change the column type.
-- ---------------------------------------------------------------------
-- site_visit_location is cardinality n, so mv_site_visit_location does
-- ST_Collect() ACROSS TILES. Three things I could not determine from the DDL:
--
--   1. If a resource's tiles hold different geometry TYPES (a point boundary
--      and a polygon boundary), ST_Collect returns a GEOMETRYCOLLECTION.
--      Plenty of downstream GIS clients - and some PostGIS functions - choke on
--      those. If this returns mixed types, decide now: cast to multipolygon,
--      keep separate typed columns, or accept GEOMETRYCOLLECTION knowingly.
--
--   2. SRID. The source view already ST_Transform()s to 4326, so this should be
--      uniformly 4326. Confirm - a stray 0 or 3005 (BC Albers) would poison the
--      GiST index and every spatial join.
--
--   3. Validity. A GiST index does not care about invalid geometry; ST_Intersects
--      and friends do. Self-intersecting boundary polygons are common in this
--      kind of data.
SELECT ST_GeometryType(site_visit_location)        AS geom_type,
       ST_SRID(site_visit_location)                AS srid,
       count(*)                                    AS tiles,
       count(*) FILTER (WHERE NOT ST_IsValid(site_visit_location)) AS invalid,
       count(*) FILTER (WHERE ST_IsEmpty(site_visit_location))     AS empty
FROM site_visit.site_visit_location
WHERE site_visit_location IS NOT NULL
GROUP BY 1, 2
ORDER BY 3 DESC;

-- C2. Which resources will produce a mixed-type collection after ST_Collect?
--     Non-zero -> your site_visit_geom column will contain GEOMETRYCOLLECTIONs.
SELECT count(*) AS resources_with_mixed_geom_types
FROM (
    SELECT resourceinstanceid
    FROM site_visit.site_visit_location
    WHERE site_visit_location IS NOT NULL
    GROUP BY resourceinstanceid
    HAVING count(DISTINCT ST_GeometryType(site_visit_location)) > 1
) m;


-- =====================================================================
-- D. LANGUAGES.  Hardcoding 'en' may be dropping data.
-- ---------------------------------------------------------------------
-- Every i18n_text() call defaults to lang => 'en'. If tiles carry content in
-- other languages, that content is silently unreachable through this stack.
-- Given the domain (BC archaeology, Indigenous place names), this is not a
-- theoretical concern - a name recorded in an Indigenous language would be
-- invisible if 'en' is present-but-empty on the same node.
--
-- If anything other than 'en' shows up: either expose the whole i18n object
-- instead of flattening, or add a second column per node (name / name_all).
SELECT lang, count(*) AS values_present
FROM (
    SELECT jsonb_object_keys(name) AS lang FROM site_visit.new_site_names WHERE jsonb_typeof(name) = 'object'
    UNION ALL
    SELECT jsonb_object_keys(project_description) FROM site_visit.site_visit_details WHERE jsonb_typeof(project_description) = 'object'
    UNION ALL
    SELECT jsonb_object_keys(remark) FROM site_visit.general_remark WHERE jsonb_typeof(remark) = 'object'
    UNION ALL
    SELECT jsonb_object_keys(cultural_material_details) FROM site_visit.cultural_material WHERE jsonb_typeof(cultural_material_details) = 'object'
    UNION ALL
    SELECT jsonb_object_keys(location_and_access) FROM site_visit.site_visit_location WHERE jsonb_typeof(location_and_access) = 'object'
) l
GROUP BY lang ORDER BY 2 DESC;

-- D2. Nodes where 'en' exists but is EMPTY while another language has content.
--     These are the rows that would silently blank out. Expect 0.
SELECT count(*) AS would_blank_out
FROM site_visit.new_site_names
WHERE jsonb_typeof(name) = 'object'
  AND COALESCE(name -> 'en' ->> 'value', '') = ''
  AND EXISTS (SELECT 1 FROM jsonb_each(name) e WHERE COALESCE(e.value ->> 'value', '') <> '');


-- =====================================================================
-- E. SCALE.  Sets your refresh budget and tells you if this design holds.
-- ---------------------------------------------------------------------
-- If resources is in the low thousands this whole stack refreshes in seconds
-- and you can run it on a cron. If it is in the millions, or if max_images per
-- resource is large, revisit before committing downstream apps to it.
SELECT
    (SELECT count(*) FROM site_visit.instances)              AS resources,
    (SELECT count(*) FROM site_visit.cultural_material)       AS cultural_material_tiles,
    (SELECT count(*) FROM site_visit.site_images)             AS image_tiles,
    (SELECT count(*) FROM site_visit.site_visit_location)     AS location_tiles,
    (SELECT max(c) FROM (SELECT count(*) c FROM site_visit.site_images
                          GROUP BY resourceinstanceid) x)     AS max_images_one_resource,
    (SELECT max(c) FROM (SELECT count(*) c FROM site_visit.site_visit_location
                          GROUP BY resourceinstanceid) x)     AS max_location_tiles_one_resource;


-- =====================================================================
-- F. COLLISIONS.  The stack opens with DROP ... CASCADE. Check what that eats.
-- ---------------------------------------------------------------------
-- If any of these names already exist and something depends on them, CASCADE
-- will drop the dependents too, without asking. Expect 0 rows on a clean build.
SELECT c.relkind, n.nspname, c.relname,
       (SELECT count(*) FROM pg_depend d
         WHERE d.refobjid = c.oid AND d.deptype = 'n') AS dependent_objects
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE (n.nspname = 'site_visit' AND (c.relname LIKE 'mv\_%' OR c.relname = 'resource'))
   OR n.nspname = 'arches_util';

-- F2. Can the migrating role actually create here?
SELECT has_schema_privilege(current_user, 'site_visit', 'CREATE') AS can_create_in_site_visit,
       current_user;


-- =====================================================================
-- G. JSONB BLOAT from embedded GeoJSON.
-- ---------------------------------------------------------------------
-- The assembled object embeds ST_AsGeoJSON(geometry) inside site_visit_location
-- AND keeps the geometry as a real column. That duplication is deliberate - the
-- typed column is what spatial queries need, the GeoJSON is what a web client
-- wants - but a detailed boundary polygon serialised at 9 decimal places is
-- large, and it will dominate the object.
--
-- If max_geojson_bytes is big (say > 1 MB), reduce precision in the stack:
--     ST_AsGeoJSON(l.site_visit_location, 7)
-- 7 decimal places is ~1cm at this latitude. 9 is sub-millimetre - noise.
SELECT
    max(length(ST_AsGeoJSON(site_visit_location)))         AS max_geojson_bytes,
    avg(length(ST_AsGeoJSON(site_visit_location)))::int    AS avg_geojson_bytes,
    max(ST_NPoints(site_visit_location))                   AS max_vertices
FROM site_visit.site_visit_location
WHERE site_visit_location IS NOT NULL;


-- =====================================================================
-- H. LABEL COMPLETENESS.  Feeds the label fix in reference_flat().
-- ---------------------------------------------------------------------
-- reference_flat() now resolves labels as:
--     prefLabel(en) -> prefLabel(any) -> altLabel(en) -> altLabel(any) -> NULL
-- and deliberately does NOT fall through to scopeNote / definition / note, so a
-- definition paragraph can never end up masquerading as a display label.
--
-- The cost of that strictness: an item carrying only notes gets a NULL label.
-- This finds them. Non-zero -> fix the controlled list, do not loosen the
-- function.
SELECT count(*) AS items_with_no_usable_label
FROM (
    SELECT item
    FROM site_visit.site_visit_location,
         LATERAL jsonb_array_elements(arches_util.as_array(boundary_type)) item
    UNION ALL
    SELECT item
    FROM site_visit.team_member,
         LATERAL jsonb_array_elements(arches_util.as_array(member_roles)) item
    UNION ALL
    SELECT item
    FROM site_visit.cultural_material,
         LATERAL jsonb_array_elements(arches_util.as_array(cultural_material_type)) item
) v
WHERE NOT EXISTS (
    SELECT 1 FROM jsonb_array_elements(arches_util.as_array(item -> 'labels')) l
    WHERE l ->> 'valuetype_id' IN ('prefLabel', 'altLabel')
);

-- H2. What valuetype_ids actually appear? Confirms prefLabel/altLabel are the
--     only display-worthy ones and shows what else is in there.
SELECT l ->> 'valuetype_id' AS valuetype, count(*)
FROM site_visit.site_visit_location,
     LATERAL jsonb_array_elements(arches_util.as_array(boundary_type)) item,
     LATERAL jsonb_array_elements(arches_util.as_array(item -> 'labels')) l
GROUP BY 1 ORDER BY 2 DESC;


-- =====================================================================
-- Note: check H requires arches_util.as_array(), which lives in the stack file.
-- Run just the "STEP 1 - HELPER FUNCTIONS" section of site_visit_mv_stack.sql
-- first (it creates nothing but functions - safe, no DROPs), then come back.
-- =====================================================================

SELECT view_name, via_view, via_tiles, distinct_tiles,
       CASE WHEN via_view = via_tiles AND via_tiles = distinct_tiles
            THEN 'ok' ELSE '*** MISMATCH ***' END AS verdict
FROM (
  SELECT 'instances' AS view_name,
         (SELECT count(*) FROM site_visit.instances),
         (SELECT count(*) FROM public.resource_instances
           WHERE graphid = '2da1c15f-1ab6-4122-9dbc-d10da693ac79'::uuid),
         (SELECT count(DISTINCT resourceinstanceid) FROM public.resource_instances
           WHERE graphid = '2da1c15f-1ab6-4122-9dbc-d10da693ac79'::uuid)
  UNION ALL SELECT 'site_visit_location',
         (SELECT count(*) FROM site_visit.site_visit_location),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = 'cf40edc0-13f0-11f0-9404-0242ac170007'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = 'cf40edc0-13f0-11f0-9404-0242ac170007'::uuid)
  UNION ALL SELECT 'biogeography',
         (SELECT count(*) FROM site_visit.biogeography),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = '6abfca2d-8f5d-458a-b128-ab8ba49c1921'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = '6abfca2d-8f5d-458a-b128-ab8ba49c1921'::uuid)
  UNION ALL SELECT 'identification',
         (SELECT count(*) FROM site_visit.identification),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = '37bdda22-140d-11f0-b9bb-0242ac170007'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = '37bdda22-140d-11f0-b9bb-0242ac170007'::uuid)
  UNION ALL SELECT 'new_site_names',
         (SELECT count(*) FROM site_visit.new_site_names),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = '6d905dbe-140d-11f0-b9bb-0242ac170007'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = '6d905dbe-140d-11f0-b9bb-0242ac170007'::uuid)
  UNION ALL SELECT 'temporary_number',
         (SELECT count(*) FROM site_visit.temporary_number),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = 'ab674670-140d-11f0-b9bb-0242ac170007'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = 'ab674670-140d-11f0-b9bb-0242ac170007'::uuid)
  UNION ALL SELECT 'site_visit_details',
         (SELECT count(*) FROM site_visit.site_visit_details),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = '887edb3a-df58-11ef-8fa3-0242ac170009'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = '887edb3a-df58-11ef-8fa3-0242ac170009'::uuid)
  UNION ALL SELECT 'site_visit_team',
         (SELECT count(*) FROM site_visit.site_visit_team),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = '0484d0b8-1410-11f0-8419-0242ac170007'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = '0484d0b8-1410-11f0-8419-0242ac170007'::uuid)
  UNION ALL SELECT 'team_member',
         (SELECT count(*) FROM site_visit.team_member),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = '0484d572-1410-11f0-8419-0242ac170007'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = '0484d572-1410-11f0-8419-0242ac170007'::uuid)
  UNION ALL SELECT 'archaeological_data',
         (SELECT count(*) FROM site_visit.archaeological_data),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = '3648fb88-1401-11f0-acd5-0242ac170007'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = '3648fb88-1401-11f0-acd5-0242ac170007'::uuid)
  UNION ALL SELECT 'cultural_material',
         (SELECT count(*) FROM site_visit.cultural_material),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = '22508fc8-1402-11f0-acd5-0242ac170007'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = '22508fc8-1402-11f0-acd5-0242ac170007'::uuid)
  UNION ALL SELECT 'stratigraphy',
         (SELECT count(*) FROM site_visit.stratigraphy),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = '720dd6dc-1408-11f0-9e93-0242ac170007'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = '720dd6dc-1408-11f0-9e93-0242ac170007'::uuid)
  UNION ALL SELECT 'archaeological_feature',
         (SELECT count(*) FROM site_visit.archaeological_feature),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = 'a0c7cc6e-1401-11f0-acd5-0242ac170007'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = 'a0c7cc6e-1401-11f0-acd5-0242ac170007'::uuid)
  UNION ALL SELECT 'chronology',
         (SELECT count(*) FROM site_visit.chronology),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = 'c1f56b08-140b-11f0-898b-0242ac170007'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = 'c1f56b08-140b-11f0-898b-0242ac170007'::uuid)
  UNION ALL SELECT 'archaeological_culture',
         (SELECT count(*) FROM site_visit.archaeological_culture),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = 'fab4ba5a-1408-11f0-9e93-0242ac170007'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = 'fab4ba5a-1408-11f0-9e93-0242ac170007'::uuid)
  UNION ALL SELECT 'site_disturbance',
         (SELECT count(*) FROM site_visit.site_disturbance),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = 'fb559106-140c-11f0-b9bb-0242ac170007'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = 'fb559106-140c-11f0-b9bb-0242ac170007'::uuid)
  UNION ALL SELECT 'additional_site_typology',
         (SELECT count(*) FROM site_visit.additional_site_typology),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = 'c3738e14-a521-47c1-8b52-668847a8a51e'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = 'c3738e14-a521-47c1-8b52-668847a8a51e'::uuid)
  UNION ALL SELECT 'remarks_and_recommendations',
         (SELECT count(*) FROM site_visit.remarks_and_recommendations),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = '77789d46-61ab-11f0-be7c-3a7a4e6803c5'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = '77789d46-61ab-11f0-be7c-3a7a4e6803c5'::uuid)
  UNION ALL SELECT 'recommendation',
         (SELECT count(*) FROM site_visit.recommendation),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = '8cf43a0e-61ab-11f0-be7c-3a7a4e6803c5'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = '8cf43a0e-61ab-11f0-be7c-3a7a4e6803c5'::uuid)
  UNION ALL SELECT 'general_remark',
         (SELECT count(*) FROM site_visit.general_remark),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = '9625020c-61ab-11f0-be7c-3a7a4e6803c5'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = '9625020c-61ab-11f0-be7c-3a7a4e6803c5'::uuid)
  UNION ALL SELECT 'ancestral_remains',
         (SELECT count(*) FROM site_visit.ancestral_remains),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = '6f96f910-5049-11f0-91cd-0242ac170006'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = '6f96f910-5049-11f0-91cd-0242ac170006'::uuid)
  UNION ALL SELECT 'related_documents',
         (SELECT count(*) FROM site_visit.related_documents),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = '44713ace-babc-4ebe-b2f6-084ed0060f2c'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = '44713ace-babc-4ebe-b2f6-084ed0060f2c'::uuid)
  UNION ALL SELECT 'related_site_documents',
         (SELECT count(*) FROM site_visit.related_site_documents),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = '55f5927c-8279-4864-ba1d-2f288ca46fcf'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = '55f5927c-8279-4864-ba1d-2f288ca46fcf'::uuid)
  UNION ALL SELECT 'publication_reference',
         (SELECT count(*) FROM site_visit.publication_reference),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = '6ac56e05-8c19-4ef3-9f3b-f5921c278e17'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = '6ac56e05-8c19-4ef3-9f3b-f5921c278e17'::uuid)
  UNION ALL SELECT 'site_images',
         (SELECT count(*) FROM site_visit.site_images),
         (SELECT count(*)          FROM public.tiles WHERE nodegroupid = 'a6536975-292e-47d1-8ebe-7e83092438bd'::uuid),
         (SELECT count(DISTINCT tileid) FROM public.tiles WHERE nodegroupid = 'a6536975-292e-47d1-8ebe-7e83092438bd'::uuid)
) x(view_name, via_view, via_tiles, distinct_tiles)
ORDER BY verdict DESC, view_name;


-- =====================================================================
-- VALUE-LEVEL SPOT CHECK
-- Row counts matching is necessary but not sufficient - it would not catch a
-- mistyped node uuid, which would silently produce NULLs. Every node uuid in the
-- v2 stack was transcribed by hand from the view DDL, so this is worth running.
--
-- Any node uuid that appears in NO tile is either mistyped or genuinely unused.
-- Cross-check anything that comes back against the graph before shipping.
-- =====================================================================
WITH used(ng, nodeid, alias) AS (VALUES
    ('cf40edc0-13f0-11f0-9404-0242ac170007','9aea2913-e4ee-43dd-904c-abee908f61b6','boundary_type'),
    ('cf40edc0-13f0-11f0-9404-0242ac170007','cf40f158-13f0-11f0-9404-0242ac170007','latest_edit_type'),
    ('cf40edc0-13f0-11f0-9404-0242ac170007','cca03a72-13fe-11f0-99e9-0242ac170007','location_and_access'),
    ('cf40edc0-13f0-11f0-9404-0242ac170007','cf40f40a-13f0-11f0-9404-0242ac170007','accuracy_remarks'),
    ('6abfca2d-8f5d-458a-b128-ab8ba49c1921','5270c773-125c-4223-868e-badeb5cf5f78','biogeography_type'),
    ('6abfca2d-8f5d-458a-b128-ab8ba49c1921','5c7d9c33-c53e-45ea-b503-d4bbeaa9e31c','biogeography_name'),
    ('6abfca2d-8f5d-458a-b128-ab8ba49c1921','95e5f9b6-71cd-4769-b365-9155442954ec','biogeography_description'),
    ('6d905dbe-140d-11f0-b9bb-0242ac170007','6d90619c-140d-11f0-b9bb-0242ac170007','name'),
    ('6d905dbe-140d-11f0-b9bb-0242ac170007','6d9065d4-140d-11f0-b9bb-0242ac170007','name_type'),
    ('6d905dbe-140d-11f0-b9bb-0242ac170007','6d9066ce-140d-11f0-b9bb-0242ac170007','name_remarks'),
    ('6d905dbe-140d-11f0-b9bb-0242ac170007','6d9063d6-140d-11f0-b9bb-0242ac170007','assigned_or_reported_by'),
    ('6d905dbe-140d-11f0-b9bb-0242ac170007','6d9067be-140d-11f0-b9bb-0242ac170007','assigned_or_reported_date'),
    ('ab674670-140d-11f0-b9bb-0242ac170007','ab674670-140d-11f0-b9bb-0242ac170007','temporary_number'),
    ('ab674670-140d-11f0-b9bb-0242ac170007','c85b4e24-140e-11f0-8419-0242ac170007','temporary_number_assigned_by'),
    ('ab674670-140d-11f0-b9bb-0242ac170007','e3dd076e-140e-11f0-8419-0242ac170007','temporary_number_assigned_date'),
    ('887edb3a-df58-11ef-8fa3-0242ac170009','e39372c4-df58-11ef-8fa3-0242ac170009','site_visit_type'),
    ('887edb3a-df58-11ef-8fa3-0242ac170009','fb01d6a1-cac8-4b16-8f2c-5472213aeec6','is_site_visit_permitted'),
    ('887edb3a-df58-11ef-8fa3-0242ac170009','745b0462-140f-11f0-8419-0242ac170007','first_date_of_site_visit'),
    ('887edb3a-df58-11ef-8fa3-0242ac170009','1de04042-df59-11ef-8fa3-0242ac170009','last_date_of_site_visit'),
    ('887edb3a-df58-11ef-8fa3-0242ac170009','fbfbb0a6-df58-11ef-8fa3-0242ac170009','project_description'),
    ('887edb3a-df58-11ef-8fa3-0242ac170009','69273f50-4c9c-11f0-9f73-0242ac170007','affiliation'),
    ('887edb3a-df58-11ef-8fa3-0242ac170009','cd722a58-df58-11ef-8fa3-0242ac170009','archaeological_site'),
    ('887edb3a-df58-11ef-8fa3-0242ac170009','b03790fe-df58-11ef-8fa3-0242ac170009','associated_permit'),
    ('887edb3a-df58-11ef-8fa3-0242ac170009','4fb2db52-1410-11f0-8419-0242ac170007','site_form_authors'),
    ('0484d572-1410-11f0-8419-0242ac170007','0484d572-1410-11f0-8419-0242ac170007','team_member'),
    ('0484d572-1410-11f0-8419-0242ac170007','0484d69e-1410-11f0-8419-0242ac170007','member_roles'),
    ('0484d572-1410-11f0-8419-0242ac170007','0484d428-1410-11f0-8419-0242ac170007','was_on_site'),
    ('22508fc8-1402-11f0-acd5-0242ac170007','4abf8e50-1402-11f0-acd5-0242ac170007','cultural_material_type'),
    ('22508fc8-1402-11f0-acd5-0242ac170007','5d4e5254-1402-11f0-acd5-0242ac170007','cultural_material_status'),
    ('22508fc8-1402-11f0-acd5-0242ac170007','b029a3c0-1402-11f0-a830-0242ac170007','cultural_material_details'),
    ('22508fc8-1402-11f0-acd5-0242ac170007','2423be32-1403-11f0-ae97-0242ac170007','number_of_artifacts'),
    ('22508fc8-1402-11f0-acd5-0242ac170007','3787b9de-5cd2-11f0-b2ee-0242ac170007','repository'),
    ('720dd6dc-1408-11f0-9e93-0242ac170007','720dd6dc-1408-11f0-9e93-0242ac170007','stratigraphy'),
    ('a0c7cc6e-1401-11f0-acd5-0242ac170007','a0c7cc6e-1401-11f0-acd5-0242ac170007','archaeological_feature'),
    ('a0c7cc6e-1401-11f0-acd5-0242ac170007','a0c7d01a-1401-11f0-acd5-0242ac170007','feature_count'),
    ('a0c7cc6e-1401-11f0-acd5-0242ac170007','a0c7d128-1401-11f0-acd5-0242ac170007','feature_remarks'),
    ('c1f56b08-140b-11f0-898b-0242ac170007','c1f5724c-140b-11f0-898b-0242ac170007','start_year'),
    ('c1f56b08-140b-11f0-898b-0242ac170007','c1f576d4-140b-11f0-898b-0242ac170007','start_year_qualifier'),
    ('c1f56b08-140b-11f0-898b-0242ac170007','c1f575ee-140b-11f0-898b-0242ac170007','start_year_calendar'),
    ('c1f56b08-140b-11f0-898b-0242ac170007','c1f57418-140b-11f0-898b-0242ac170007','end_year'),
    ('c1f56b08-140b-11f0-898b-0242ac170007','c1f56e78-140b-11f0-898b-0242ac170007','end_year_qualifier'),
    ('c1f56b08-140b-11f0-898b-0242ac170007','c1f56f86-140b-11f0-898b-0242ac170007','end_year_calendar'),
    ('c1f56b08-140b-11f0-898b-0242ac170007','c1f57166-140b-11f0-898b-0242ac170007','determination_method'),
    ('c1f56b08-140b-11f0-898b-0242ac170007','c1f57332-140b-11f0-898b-0242ac170007','information_source'),
    ('c1f56b08-140b-11f0-898b-0242ac170007','c1f57080-140b-11f0-898b-0242ac170007','chronology_remarks'),
    ('fab4ba5a-1408-11f0-9e93-0242ac170007','fab4ba5a-1408-11f0-9e93-0242ac170007','archaeological_culture'),
    ('fab4ba5a-1408-11f0-9e93-0242ac170007','fab4bde8-1408-11f0-9e93-0242ac170007','culture_remarks'),
    ('fb559106-140c-11f0-b9bb-0242ac170007','fb559480-140c-11f0-b9bb-0242ac170007','disturbance_period'),
    ('fb559106-140c-11f0-b9bb-0242ac170007','fb5595c0-140c-11f0-b9bb-0242ac170007','disturbance_cause'),
    ('fb559106-140c-11f0-b9bb-0242ac170007','fb5596b0-140c-11f0-b9bb-0242ac170007','disturbance_remarks'),
    ('c3738e14-a521-47c1-8b52-668847a8a51e','d6765cc8-8dec-431b-bbb5-950567e6ed1c','typology_class'),
    ('c3738e14-a521-47c1-8b52-668847a8a51e','c98387af-e430-4317-b222-9f2191194817','typology_remark'),
    ('8cf43a0e-61ab-11f0-be7c-3a7a4e6803c5','8cf43cd4-61ab-11f0-be7c-3a7a4e6803c5','recorders_recommendation'),
    ('8cf43a0e-61ab-11f0-be7c-3a7a4e6803c5','fadb061b-2be7-4a0b-810a-51d8cee25bf8','archaeology_branch_recommendation'),
    ('9625020c-61ab-11f0-be7c-3a7a4e6803c5','9625068a-61ab-11f0-be7c-3a7a4e6803c5','remark'),
    ('9625020c-61ab-11f0-be7c-3a7a4e6803c5','962505cc-61ab-11f0-be7c-3a7a4e6803c5','remark_date'),
    ('9625020c-61ab-11f0-be7c-3a7a4e6803c5','962504dc-61ab-11f0-be7c-3a7a4e6803c5','remark_source'),
    ('6f96f910-5049-11f0-91cd-0242ac170006','6f96fb9a-5049-11f0-91cd-0242ac170006','ancestral_remains_type'),
    ('6f96f910-5049-11f0-91cd-0242ac170006','6f96fd5c-5049-11f0-91cd-0242ac170006','ancestral_remains_status'),
    ('6f96f910-5049-11f0-91cd-0242ac170006','6f96fe2e-5049-11f0-91cd-0242ac170006','ancestral_remains_remarks'),
    ('6f96f910-5049-11f0-91cd-0242ac170006','a87dd01e-5ce2-11f0-a419-0242ac170007','ancestral_remains_repository'),
    ('6f96f910-5049-11f0-91cd-0242ac170006','6f96fef6-5049-11f0-91cd-0242ac170006','minimum_number_of_individuals'),
    ('6f96f910-5049-11f0-91cd-0242ac170006','6f96fc94-5049-11f0-91cd-0242ac170006','multiple_burials'),
    ('55f5927c-8279-4864-ba1d-2f288ca46fcf','55f5927c-8279-4864-ba1d-2f288ca46fcf','related_site_documents'),
    ('55f5927c-8279-4864-ba1d-2f288ca46fcf','acbdadfa-2ccf-4a68-9497-56d36dbd1021','related_document_type'),
    ('55f5927c-8279-4864-ba1d-2f288ca46fcf','844ae10f-b38b-4706-8fac-8804d04ab05e','related_document_description'),
    ('6ac56e05-8c19-4ef3-9f3b-f5921c278e17','6ac56e05-8c19-4ef3-9f3b-f5921c278e17','publication_reference'),
    ('a6536975-292e-47d1-8ebe-7e83092438bd','a6536975-292e-47d1-8ebe-7e83092438bd','site_images'),
    ('a6536975-292e-47d1-8ebe-7e83092438bd','696b4699-bc65-4d0e-8d48-f2a211fe5e3a','primary_image'),
    ('a6536975-292e-47d1-8ebe-7e83092438bd','98c6f7ee-5c7f-4287-aeed-0168e5c40773','image_type'),
    ('a6536975-292e-47d1-8ebe-7e83092438bd','c0dbd7b1-9c2b-4c27-96f3-17cb5aad7d25','image_view'),
    ('a6536975-292e-47d1-8ebe-7e83092438bd','10d83dfd-49d8-4bf3-9977-4acbc809b7b8','image_description'),
    ('a6536975-292e-47d1-8ebe-7e83092438bd','9bd92cab-7995-4940-9547-073e2eb505ac','image_features'),
    ('a6536975-292e-47d1-8ebe-7e83092438bd','d20d1438-701d-47e9-8f93-7a460f3bba75','photographer'),
    ('a6536975-292e-47d1-8ebe-7e83092438bd','7b7f1f4c-df01-4881-b9f3-495fc9a968bc','copyright'),
    ('a6536975-292e-47d1-8ebe-7e83092438bd','2454579e-6884-4d1d-82f3-724f62ce4d4f','image_date')
)
SELECT u.alias,
       u.nodeid,
       -- is the node uuid real, i.e. does it exist in `nodes` for this nodegroup?
       EXISTS (SELECT 1 FROM nodes n
                WHERE n.nodeid = u.nodeid::uuid
                  AND n.nodegroupid = u.ng::uuid)                     AS node_exists,
       -- does any tile actually carry a value at that key?
       (SELECT count(*) FROM public.tiles t
         WHERE t.nodegroupid = u.ng::uuid
           AND t.tiledata ? u.nodeid)                                 AS tiles_with_key
FROM used u
ORDER BY node_exists, tiles_with_key, u.alias;