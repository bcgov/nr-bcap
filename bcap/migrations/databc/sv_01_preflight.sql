-- =====================================================================
--  site_visit :: PREFLIGHT.  Run ALL of this and read the results BEFORE building.
--  Ordered by blast radius. A and C can change the DDL.
-- =====================================================================

-- =====================================================================
-- A. CARDINALITY.  THE LOAD-BEARING ASSUMPTION.
-- Every array-vs-object decision in the stack comes from this. Expected:
--   n   site_visit_location                    parent=-
--   n   biogeography                           parent=site_visit_location
--   1   identification                         parent=-
--   n   new_site_names                         parent=identification
--   1   temporary_number                       parent=identification
--   1   site_visit_details                     parent=-
--   1   site_visit_team                        parent=site_visit_details
--   n   team_member                            parent=site_visit_team
--   1   archaeological_data                    parent=-
--   n   cultural_material                      parent=archaeological_data
--   n   stratigraphy                           parent=archaeological_data
--   n   archaeological_feature                 parent=archaeological_data
--   n   chronology                             parent=archaeological_data
--   n   archaeological_culture                 parent=archaeological_data
--   n   site_disturbance                       parent=archaeological_data
--   n   additional_site_typology               parent=archaeological_data
--   1   remarks_and_recommendations            parent=-
--   n   recommendation                         parent=remarks_and_recommendations
--   n   general_remark                         parent=remarks_and_recommendations
--   n   ancestral_remains                      parent=-
--   1   related_documents                      parent=-
--   n   related_site_documents                 parent=related_documents
--   n   publication_reference                  parent=related_documents
--   n   site_images                            parent=related_documents
--
-- ANY disagreement -> fix sv_spec.py and regenerate. Do not build and see.
SELECT n.name AS view_name, ng.cardinality, pn.name AS parent, ng.nodegroupid
FROM node_groups ng
JOIN nodes n              ON n.nodeid = ng.nodegroupid
LEFT JOIN node_groups png ON png.nodegroupid = ng.parentnodegroupid
LEFT JOIN nodes pn        ON pn.nodeid = png.nodegroupid
WHERE n.graphid = '2da1c15f-1ab6-4122-9dbc-d10da693ac79'
ORDER BY COALESCE(pn.name,''), n.name;


-- =====================================================================
-- B. EQUIVALENCE: is dropping the edit_log join safe?
-- Both edit_log joins in the generated views are LEFT JOINs, so the anti-join
-- only collapses fan-out - it never removes a tile. If that holds, the row set
-- is identical to tiles filtered by nodegroupid, and this stack is sound.
--
-- IF via_view < via_tiles ANYWHERE: STOP. Do not build.
-- =====================================================================
SELECT view_name, via_view, via_tiles,
       CASE WHEN via_view = via_tiles THEN 'ok' ELSE '*** MISMATCH ***' END AS verdict
FROM (
  SELECT 'instances' AS view_name,
         (SELECT count(*) FROM site_visit.instances),
         (SELECT count(*) FROM public.resource_instances WHERE graphid = '2da1c15f-1ab6-4122-9dbc-d10da693ac79'::uuid)
  UNION ALL SELECT 'site_visit_location',
         (SELECT count(*) FROM site_visit.site_visit_location),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'cf40edc0-13f0-11f0-9404-0242ac170007'::uuid)
  UNION ALL SELECT 'biogeography',
         (SELECT count(*) FROM site_visit.biogeography),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '6abfca2d-8f5d-458a-b128-ab8ba49c1921'::uuid)
  UNION ALL SELECT 'identification',
         (SELECT count(*) FROM site_visit.identification),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '37bdda22-140d-11f0-b9bb-0242ac170007'::uuid)
  UNION ALL SELECT 'new_site_names',
         (SELECT count(*) FROM site_visit.new_site_names),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '6d905dbe-140d-11f0-b9bb-0242ac170007'::uuid)
  UNION ALL SELECT 'temporary_number',
         (SELECT count(*) FROM site_visit.temporary_number),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'ab674670-140d-11f0-b9bb-0242ac170007'::uuid)
  UNION ALL SELECT 'site_visit_details',
         (SELECT count(*) FROM site_visit.site_visit_details),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '887edb3a-df58-11ef-8fa3-0242ac170009'::uuid)
  UNION ALL SELECT 'site_visit_team',
         (SELECT count(*) FROM site_visit.site_visit_team),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '0484d0b8-1410-11f0-8419-0242ac170007'::uuid)
  UNION ALL SELECT 'team_member',
         (SELECT count(*) FROM site_visit.team_member),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '0484d572-1410-11f0-8419-0242ac170007'::uuid)
  UNION ALL SELECT 'archaeological_data',
         (SELECT count(*) FROM site_visit.archaeological_data),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '3648fb88-1401-11f0-acd5-0242ac170007'::uuid)
  UNION ALL SELECT 'cultural_material',
         (SELECT count(*) FROM site_visit.cultural_material),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '22508fc8-1402-11f0-acd5-0242ac170007'::uuid)
  UNION ALL SELECT 'stratigraphy',
         (SELECT count(*) FROM site_visit.stratigraphy),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '720dd6dc-1408-11f0-9e93-0242ac170007'::uuid)
  UNION ALL SELECT 'archaeological_feature',
         (SELECT count(*) FROM site_visit.archaeological_feature),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'a0c7cc6e-1401-11f0-acd5-0242ac170007'::uuid)
  UNION ALL SELECT 'chronology',
         (SELECT count(*) FROM site_visit.chronology),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'c1f56b08-140b-11f0-898b-0242ac170007'::uuid)
  UNION ALL SELECT 'archaeological_culture',
         (SELECT count(*) FROM site_visit.archaeological_culture),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'fab4ba5a-1408-11f0-9e93-0242ac170007'::uuid)
  UNION ALL SELECT 'site_disturbance',
         (SELECT count(*) FROM site_visit.site_disturbance),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'fb559106-140c-11f0-b9bb-0242ac170007'::uuid)
  UNION ALL SELECT 'additional_site_typology',
         (SELECT count(*) FROM site_visit.additional_site_typology),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'c3738e14-a521-47c1-8b52-668847a8a51e'::uuid)
  UNION ALL SELECT 'remarks_and_recommendations',
         (SELECT count(*) FROM site_visit.remarks_and_recommendations),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '77789d46-61ab-11f0-be7c-3a7a4e6803c5'::uuid)
  UNION ALL SELECT 'recommendation',
         (SELECT count(*) FROM site_visit.recommendation),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '8cf43a0e-61ab-11f0-be7c-3a7a4e6803c5'::uuid)
  UNION ALL SELECT 'general_remark',
         (SELECT count(*) FROM site_visit.general_remark),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '9625020c-61ab-11f0-be7c-3a7a4e6803c5'::uuid)
  UNION ALL SELECT 'ancestral_remains',
         (SELECT count(*) FROM site_visit.ancestral_remains),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '6f96f910-5049-11f0-91cd-0242ac170006'::uuid)
  UNION ALL SELECT 'related_documents',
         (SELECT count(*) FROM site_visit.related_documents),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '44713ace-babc-4ebe-b2f6-084ed0060f2c'::uuid)
  UNION ALL SELECT 'related_site_documents',
         (SELECT count(*) FROM site_visit.related_site_documents),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '55f5927c-8279-4864-ba1d-2f288ca46fcf'::uuid)
  UNION ALL SELECT 'publication_reference',
         (SELECT count(*) FROM site_visit.publication_reference),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '6ac56e05-8c19-4ef3-9f3b-f5921c278e17'::uuid)
  UNION ALL SELECT 'site_images',
         (SELECT count(*) FROM site_visit.site_images),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'a6536975-292e-47d1-8ebe-7e83092438bd'::uuid)
) x(view_name, via_view, via_tiles)
ORDER BY verdict DESC, view_name;


-- =====================================================================
-- C. NODE UUID SANITY.  A mistyped uuid does NOT error - tiledata -> '<wrong>'
-- just returns NULL, and you ship a permanently-empty column. Expect
-- node_exists = true on EVERY row.
-- =====================================================================
WITH used(ng, nodeid, alias) AS (VALUES
    ('cf40edc0-13f0-11f0-9404-0242ac170007','9aea2913-e4ee-43dd-904c-abee908f61b6','boundary_type'),
    ('cf40edc0-13f0-11f0-9404-0242ac170007','cf40f158-13f0-11f0-9404-0242ac170007','latest_edit_type'),
    ('cf40edc0-13f0-11f0-9404-0242ac170007','cca03a72-13fe-11f0-99e9-0242ac170007','location_and_access'),
    ('cf40edc0-13f0-11f0-9404-0242ac170007','cf40f40a-13f0-11f0-9404-0242ac170007','accuracy_remarks'),
    ('cf40edc0-13f0-11f0-9404-0242ac170007','cf40edc0-13f0-11f0-9404-0242ac170007','site_visit_location'),
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
SELECT u.alias, u.nodeid,
       EXISTS (SELECT 1 FROM nodes n WHERE n.nodeid = u.nodeid::uuid
                 AND n.nodegroupid = u.ng::uuid)                      AS node_exists,
       (SELECT count(*) FROM public.tiles t
         WHERE t.nodegroupid = u.ng::uuid AND t.tiledata ? u.nodeid)  AS tiles_with_key
FROM used u ORDER BY node_exists, tiles_with_key, u.alias;


-- =====================================================================
-- D. ORPHAN CHILD TILES.  Silent data loss if non-zero.
-- Each branch drives off the PARENT tile and LEFT JOINs children. A child whose
-- parenttileid points at a parent that is not in the parent nodegroup simply
-- VANISHES - no error, no constraint, no clue. Expect 0 everywhere.
-- =====================================================================
SELECT 'biogeography' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '6abfca2d-8f5d-458a-b128-ab8ba49c1921'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = 'cf40edc0-13f0-11f0-9404-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'new_site_names' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '6d905dbe-140d-11f0-b9bb-0242ac170007'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '37bdda22-140d-11f0-b9bb-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'temporary_number' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = 'ab674670-140d-11f0-b9bb-0242ac170007'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '37bdda22-140d-11f0-b9bb-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'site_visit_team' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '0484d0b8-1410-11f0-8419-0242ac170007'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '887edb3a-df58-11ef-8fa3-0242ac170009'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'team_member' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '0484d572-1410-11f0-8419-0242ac170007'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '0484d0b8-1410-11f0-8419-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'cultural_material' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '22508fc8-1402-11f0-acd5-0242ac170007'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '3648fb88-1401-11f0-acd5-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'stratigraphy' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '720dd6dc-1408-11f0-9e93-0242ac170007'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '3648fb88-1401-11f0-acd5-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'archaeological_feature' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = 'a0c7cc6e-1401-11f0-acd5-0242ac170007'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '3648fb88-1401-11f0-acd5-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'chronology' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = 'c1f56b08-140b-11f0-898b-0242ac170007'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '3648fb88-1401-11f0-acd5-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'archaeological_culture' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = 'fab4ba5a-1408-11f0-9e93-0242ac170007'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '3648fb88-1401-11f0-acd5-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'site_disturbance' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = 'fb559106-140c-11f0-b9bb-0242ac170007'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '3648fb88-1401-11f0-acd5-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'additional_site_typology' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = 'c3738e14-a521-47c1-8b52-668847a8a51e'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '3648fb88-1401-11f0-acd5-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'recommendation' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '8cf43a0e-61ab-11f0-be7c-3a7a4e6803c5'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '77789d46-61ab-11f0-be7c-3a7a4e6803c5'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'general_remark' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '9625020c-61ab-11f0-be7c-3a7a4e6803c5'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '77789d46-61ab-11f0-be7c-3a7a4e6803c5'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'related_site_documents' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '55f5927c-8279-4864-ba1d-2f288ca46fcf'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '44713ace-babc-4ebe-b2f6-084ed0060f2c'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'publication_reference' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '6ac56e05-8c19-4ef3-9f3b-f5921c278e17'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '44713ace-babc-4ebe-b2f6-084ed0060f2c'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'site_images' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = 'a6536975-292e-47d1-8ebe-7e83092438bd'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '44713ace-babc-4ebe-b2f6-084ed0060f2c'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'none', 0 WHERE false;


-- =====================================================================
-- E. GEOMETRY.  Source is SRID 3857 (Web Mercator); the stack transforms to 4326
-- and the ::geometry(...,4326) casts ENFORCE it.
-- Invalid geometries are REPAIRED with ST_MakeValid so one bad polygon cannot
-- break every downstream spatial query - but repair CHANGES an authoritative
-- boundary (a bowtie becomes two polygons). Fix them at source. This finds them.
-- =====================================================================
SELECT 'site_visit_location' AS node, ST_GeometryType(geom) AS geom_type, ST_SRID(geom) AS srid,
       count(*) AS n, count(*) FILTER (WHERE NOT ST_IsValid(geom)) AS invalid
FROM public.geojson_geometries WHERE nodeid = 'cf40edc0-13f0-11f0-9404-0242ac170007'::uuid
GROUP BY 1,2,3 ORDER BY 4 DESC;

-- The specific invalid ones, with the reason. Fix these at source.
SELECT t.resourceinstanceid, g.tileid, ST_IsValidReason(ST_Transform(g.geom, 4326)) AS reason
FROM public.geojson_geometries g JOIN public.tiles t ON t.tileid = g.tileid
WHERE g.nodeid = 'cf40edc0-13f0-11f0-9404-0242ac170007'::uuid AND NOT ST_IsValid(ST_Transform(g.geom, 4326))
LIMIT 50;


-- =====================================================================
-- F. SCALE.  Sets the refresh budget.
-- =====================================================================
SELECT (SELECT count(*) FROM public.resource_instances WHERE graphid = '2da1c15f-1ab6-4122-9dbc-d10da693ac79'::uuid) AS resources,
       (SELECT count(*) FROM public.tiles t JOIN public.resource_instances r
          USING (resourceinstanceid) WHERE r.graphid = '2da1c15f-1ab6-4122-9dbc-d10da693ac79'::uuid)                  AS tiles;
