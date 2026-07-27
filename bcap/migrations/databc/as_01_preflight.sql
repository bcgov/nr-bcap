-- =====================================================================
--  archaeological_site :: PREFLIGHT.  Run ALL of this and read the results BEFORE building.
--  Ordered by blast radius. A and C can change the DDL.
-- =====================================================================

-- =====================================================================
-- A. CARDINALITY.  THE LOAD-BEARING ASSUMPTION.
-- Every array-vs-object decision in the stack comes from this. Expected:
--   1   site_boundary                          parent=-
--   n   unprotected_areas                      parent=site_boundary
--   1   identification_and_registration        parent=-
--   1   site_alert                             parent=identification_and_registration
--   n   authority                              parent=identification_and_registration
--   n   site_names                             parent=identification_and_registration
--   n   site_decision                          parent=identification_and_registration
--   n   site_location                          parent=-
--   n   biogeography                           parent=site_location
--   1   site_tenure                            parent=site_location
--   1   site_tenure_remarks                    parent=site_tenure
--   1   site_tenure_type                       parent=site_tenure
--   1   elevation                              parent=site_location
--   n   elevation_comments                     parent=elevation
--   n   bc_property_address                    parent=site_location
--   n   bc_property_legal_description          parent=bc_property_address
--   1   archaeological_data                    parent=-
--   n   site_typology                          parent=archaeological_data
--   n   site_record_admin                      parent=-
--   n   external_url                           parent=-
--   1   ancestral_remains                      parent=-
--   1   restricted_ancestral_remains_remark    parent=ancestral_remains
--   1   remarks_and_restricted_information     parent=-
--   n   remark_keyword                         parent=remarks_and_restricted_information
--   n   general_remark_information             parent=remarks_and_restricted_information
--   n   contravention_document                 parent=remarks_and_restricted_information
--   n   restricted_document                    parent=remarks_and_restricted_information
--   n   hca_contravention                      parent=remarks_and_restricted_information
--   n   restricted_information                 parent=remarks_and_restricted_information
--   n   conviction                             parent=remarks_and_restricted_information
--   1   related_documents                      parent=-
--   n   related_site_documents                 parent=related_documents
--   n   publication_reference                  parent=related_documents
--   n   site_images                            parent=related_documents
--
-- ANY disagreement -> fix as_spec.py and regenerate. Do not build and see.
SELECT n.name AS view_name, ng.cardinality, pn.name AS parent, ng.nodegroupid
FROM node_groups ng
JOIN nodes n              ON n.nodeid = ng.nodegroupid
LEFT JOIN node_groups png ON png.nodegroupid = ng.parentnodegroupid
LEFT JOIN nodes pn        ON pn.nodeid = png.nodegroupid
WHERE n.graphid = 'cef9c510-e3e6-4057-ac08-89ad926180b4'
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
         (SELECT count(*) FROM archaeological_site.instances),
         (SELECT count(*) FROM public.resource_instances WHERE graphid = 'cef9c510-e3e6-4057-ac08-89ad926180b4'::uuid)
  UNION ALL SELECT 'site_boundary',
         (SELECT count(*) FROM archaeological_site.site_boundary),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'b18223c2-13ef-11f0-8695-0242ac170007'::uuid)
  UNION ALL SELECT 'unprotected_areas',
         (SELECT count(*) FROM archaeological_site.unprotected_areas),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '7c8eb1f8-44e2-4239-afaa-9cbf1fadf160'::uuid)
  UNION ALL SELECT 'identification_and_registration',
         (SELECT count(*) FROM archaeological_site.identification_and_registration),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '034d1c32-13f2-11f0-9ff8-0242ac170007'::uuid)
  UNION ALL SELECT 'site_alert',
         (SELECT count(*) FROM archaeological_site.site_alert),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '00e2b556-1979-11f0-8713-0242ac170008'::uuid)
  UNION ALL SELECT 'authority',
         (SELECT count(*) FROM archaeological_site.authority),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '034d1fac-13f2-11f0-9ff8-0242ac170007'::uuid)
  UNION ALL SELECT 'site_names',
         (SELECT count(*) FROM archaeological_site.site_names),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'd60b1b28-35f4-11f0-afbc-0242ac170008'::uuid)
  UNION ALL SELECT 'site_decision',
         (SELECT count(*) FROM archaeological_site.site_decision),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'f80f08ae-1977-11f0-8713-0242ac170008'::uuid)
  UNION ALL SELECT 'site_location',
         (SELECT count(*) FROM archaeological_site.site_location),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '1b62393e-0d0f-11ed-98c2-5254008afee6'::uuid)
  UNION ALL SELECT 'biogeography',
         (SELECT count(*) FROM archaeological_site.biogeography),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '2509f4a2-197f-11f0-b2a5-0242ac170008'::uuid)
  UNION ALL SELECT 'site_tenure',
         (SELECT count(*) FROM archaeological_site.site_tenure),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '40a52cd0-197b-11f0-8d46-0242ac170008'::uuid)
  UNION ALL SELECT 'site_tenure_remarks',
         (SELECT count(*) FROM archaeological_site.site_tenure_remarks),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '4598a202-197c-11f0-b2a5-0242ac170008'::uuid)
  UNION ALL SELECT 'site_tenure_type',
         (SELECT count(*) FROM archaeological_site.site_tenure_type),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '7b8991ec-197b-11f0-8d46-0242ac170008'::uuid)
  UNION ALL SELECT 'elevation',
         (SELECT count(*) FROM archaeological_site.elevation),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'c2f9e970-01be-11f0-9078-0242ac170007'::uuid)
  UNION ALL SELECT 'elevation_comments',
         (SELECT count(*) FROM archaeological_site.elevation_comments),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'bc131e78-01bf-11f0-97f7-0242ac170007'::uuid)
  UNION ALL SELECT 'bc_property_address',
         (SELECT count(*) FROM archaeological_site.bc_property_address),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '1b622e58-0d0f-11ed-98c2-5254008afee6'::uuid)
  UNION ALL SELECT 'bc_property_legal_description',
         (SELECT count(*) FROM archaeological_site.bc_property_legal_description),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '1b622ab6-0d0f-11ed-98c2-5254008afee6'::uuid)
  UNION ALL SELECT 'archaeological_data',
         (SELECT count(*) FROM archaeological_site.archaeological_data),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '09856d8c-01c0-11f0-97f7-0242ac170007'::uuid)
  UNION ALL SELECT 'site_typology',
         (SELECT count(*) FROM archaeological_site.site_typology),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '3083c10e-01c0-11f0-97f7-0242ac170007'::uuid)
  UNION ALL SELECT 'site_record_admin',
         (SELECT count(*) FROM archaeological_site.site_record_admin),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '0684fec8-0d07-11ed-8804-5254008afee6'::uuid)
  UNION ALL SELECT 'external_url',
         (SELECT count(*) FROM archaeological_site.external_url),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '3ee73f28-ca40-11ed-af48-5254004d77d3'::uuid)
  UNION ALL SELECT 'ancestral_remains',
         (SELECT count(*) FROM archaeological_site.ancestral_remains),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '14179ca2-64ad-11f0-a4ef-6e5bb479055b'::uuid)
  UNION ALL SELECT 'restricted_ancestral_remains_remark',
         (SELECT count(*) FROM archaeological_site.restricted_ancestral_remains_remark),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '1417996e-64ad-11f0-a4ef-6e5bb479055b'::uuid)
  UNION ALL SELECT 'remarks_and_restricted_information',
         (SELECT count(*) FROM archaeological_site.remarks_and_restricted_information),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '75c91464-619f-11f0-acf4-3a7a4e6803c5'::uuid)
  UNION ALL SELECT 'remark_keyword',
         (SELECT count(*) FROM archaeological_site.remark_keyword),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'dc827931-05ed-43e4-8da6-e99c0d02dae7'::uuid)
  UNION ALL SELECT 'general_remark_information',
         (SELECT count(*) FROM archaeological_site.general_remark_information),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '05baebf6-61a5-11f0-9674-3a7a4e6803c5'::uuid)
  UNION ALL SELECT 'contravention_document',
         (SELECT count(*) FROM archaeological_site.contravention_document),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '1bebc404-61a5-11f0-9674-3a7a4e6803c5'::uuid)
  UNION ALL SELECT 'restricted_document',
         (SELECT count(*) FROM archaeological_site.restricted_document),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '250ed6fe-61a8-11f0-ad02-3a7a4e6803c5'::uuid)
  UNION ALL SELECT 'hca_contravention',
         (SELECT count(*) FROM archaeological_site.hca_contravention),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '41fb5948-61a5-11f0-9674-3a7a4e6803c5'::uuid)
  UNION ALL SELECT 'restricted_information',
         (SELECT count(*) FROM archaeological_site.restricted_information),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'b0ed31c4-61a4-11f0-9674-3a7a4e6803c5'::uuid)
  UNION ALL SELECT 'conviction',
         (SELECT count(*) FROM archaeological_site.conviction),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'c5159e8e-619f-11f0-acf4-3a7a4e6803c5'::uuid)
  UNION ALL SELECT 'related_documents',
         (SELECT count(*) FROM archaeological_site.related_documents),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '347e24f8-01d8-11f0-850c-0242ac170007'::uuid)
  UNION ALL SELECT 'related_site_documents',
         (SELECT count(*) FROM archaeological_site.related_site_documents),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '2ad161ee-50ad-11f0-a6c8-0242ac170006'::uuid)
  UNION ALL SELECT 'publication_reference',
         (SELECT count(*) FROM archaeological_site.publication_reference),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'bb157a2a-01d8-11f0-850c-0242ac170007'::uuid)
  UNION ALL SELECT 'site_images',
         (SELECT count(*) FROM archaeological_site.site_images),
         (SELECT count(*) FROM public.tiles WHERE nodegroupid = 'c81626e8-01d8-11f0-850c-0242ac170007'::uuid)
) x(view_name, via_view, via_tiles)
ORDER BY verdict DESC, view_name;


-- =====================================================================
-- C. NODE UUID SANITY.  A mistyped uuid does NOT error - tiledata -> '<wrong>'
-- just returns NULL, and you ship a permanently-empty column. Expect
-- node_exists = true on EVERY row.
-- =====================================================================
WITH used(ng, nodeid, alias) AS (VALUES
    ('b18223c2-13ef-11f0-8695-0242ac170007','b182276e-13ef-11f0-8695-0242ac170007','accuracy_remarks'),
    ('b18223c2-13ef-11f0-8695-0242ac170007','63e48668-58f0-49fa-8767-abf412f54921','site_boundary_description'),
    ('b18223c2-13ef-11f0-8695-0242ac170007','6292f704-13f0-11f0-9284-0242ac170007','latest_edit_type'),
    ('b18223c2-13ef-11f0-8695-0242ac170007','b18223c2-13ef-11f0-8695-0242ac170007','site_boundary'),
    ('7c8eb1f8-44e2-4239-afaa-9cbf1fadf160','e1f8bec7-9d0c-4f04-9dc8-718d05444105','unprotected_area_type'),
    ('7c8eb1f8-44e2-4239-afaa-9cbf1fadf160','56c7c419-e31c-4e7d-a99a-8aea3f370e52','other_unprotected_area_type'),
    ('7c8eb1f8-44e2-4239-afaa-9cbf1fadf160','7c8eb1f8-44e2-4239-afaa-9cbf1fadf160','unprotected_areas'),
    ('034d1c32-13f2-11f0-9ff8-0242ac170007','7e15332c-1c54-11f0-b5bf-0242ac170007','borden_number'),
    ('034d1c32-13f2-11f0-9ff8-0242ac170007','b442cce2-62c8-11f0-a80e-76ff5c50888d','parcel_owner_type'),
    ('034d1c32-13f2-11f0-9ff8-0242ac170007','bce307f4-62c8-11f0-a80e-76ff5c50888d','borden_number_issuance_date'),
    ('034d1c32-13f2-11f0-9ff8-0242ac170007','2255168c-1c55-11f0-9b6d-0242ac170007','register_type'),
    ('034d1c32-13f2-11f0-9ff8-0242ac170007','7158cc42-1c55-11f0-9b6d-0242ac170007','parent_site'),
    ('00e2b556-1979-11f0-8713-0242ac170008','3c5afaa2-197a-11f0-8f07-0242ac170008','alert_subject'),
    ('00e2b556-1979-11f0-8713-0242ac170008','7219d578-197a-11f0-8f07-0242ac170008','alert_details'),
    ('00e2b556-1979-11f0-8713-0242ac170008','ec331cd0-1979-11f0-93f5-0242ac170008','alert_entered_by'),
    ('00e2b556-1979-11f0-8713-0242ac170008','8511d07c-197a-11f0-8f07-0242ac170008','alert_branch_contact'),
    ('00e2b556-1979-11f0-8713-0242ac170008','387adf52-1979-11f0-8713-0242ac170008','alert_entry_date'),
    ('034d1fac-13f2-11f0-9ff8-0242ac170007','85d39c80-b92d-449f-834d-5d9b2ab3d1e8','authority_protection_type'),
    ('034d1fac-13f2-11f0-9ff8-0242ac170007','034d2e02-13f2-11f0-9ff8-0242ac170007','legislative_act'),
    ('034d1fac-13f2-11f0-9ff8-0242ac170007','034d31b8-13f2-11f0-9ff8-0242ac170007','reference_number'),
    ('034d1fac-13f2-11f0-9ff8-0242ac170007','034d2ef2-13f2-11f0-9ff8-0242ac170007','authority_description'),
    ('034d1fac-13f2-11f0-9ff8-0242ac170007','85dcf57e-1978-11f0-8713-0242ac170008','authority_start_date'),
    ('034d1fac-13f2-11f0-9ff8-0242ac170007','b36abfee-1978-11f0-8713-0242ac170008','authority_end_date'),
    ('d60b1b28-35f4-11f0-afbc-0242ac170008','d60b1fa6-35f4-11f0-afbc-0242ac170008','name'),
    ('d60b1b28-35f4-11f0-afbc-0242ac170008','d60b242e-35f4-11f0-afbc-0242ac170008','name_type'),
    ('d60b1b28-35f4-11f0-afbc-0242ac170008','d60b2514-35f4-11f0-afbc-0242ac170008','name_remarks'),
    ('d60b1b28-35f4-11f0-afbc-0242ac170008','d60b2244-35f4-11f0-afbc-0242ac170008','assigned_or_reported_by'),
    ('d60b1b28-35f4-11f0-afbc-0242ac170008','d60b25fa-35f4-11f0-afbc-0242ac170008','assigned_or_reported_date'),
    ('f80f08ae-1977-11f0-8713-0242ac170008','f80f08ae-1977-11f0-8713-0242ac170008','site_decision'),
    ('f80f08ae-1977-11f0-8713-0242ac170008','4abdfeea-8d15-4ea6-94bd-d2385d47a5ac','decision_registration_status'),
    ('f80f08ae-1977-11f0-8713-0242ac170008','f80f115a-1977-11f0-8713-0242ac170008','decision_description'),
    ('f80f08ae-1977-11f0-8713-0242ac170008','f80f0d4a-1977-11f0-8713-0242ac170008','decision_made_by'),
    ('f80f08ae-1977-11f0-8713-0242ac170008','f80f0c00-1977-11f0-8713-0242ac170008','decision_date'),
    ('f80f08ae-1977-11f0-8713-0242ac170008','f80f0f34-1977-11f0-8713-0242ac170008','recommended_by'),
    ('f80f08ae-1977-11f0-8713-0242ac170008','f80f106a-1977-11f0-8713-0242ac170008','recommendation_date'),
    ('2509f4a2-197f-11f0-b2a5-0242ac170008','7044fb24-197f-11f0-9fc9-0242ac170008','biogeography_type'),
    ('2509f4a2-197f-11f0-b2a5-0242ac170008','96df3a2e-197f-11f0-9fc9-0242ac170008','biogeography_name'),
    ('2509f4a2-197f-11f0-b2a5-0242ac170008','aad2e7e2-197f-11f0-9fc9-0242ac170008','biogeography_description'),
    ('4598a202-197c-11f0-b2a5-0242ac170008','4598a202-197c-11f0-b2a5-0242ac170008','site_tenure_remarks'),
    ('7b8991ec-197b-11f0-8d46-0242ac170008','7b8991ec-197b-11f0-8d46-0242ac170008','site_tenure_type'),
    ('7b8991ec-197b-11f0-8d46-0242ac170008','b2fcabe0-197c-11f0-b2a5-0242ac170008','site_tenure_identifier'),
    ('c2f9e970-01be-11f0-9078-0242ac170007','55b8225e-01bf-11f0-97f7-0242ac170007','gis_lower_elevation'),
    ('c2f9e970-01be-11f0-9078-0242ac170007','547414ac-01bf-11f0-97f7-0242ac170007','gis_upper_elevation'),
    ('bc131e78-01bf-11f0-97f7-0242ac170007','bc131e78-01bf-11f0-97f7-0242ac170007','elevation_comments'),
    ('1b622e58-0d0f-11ed-98c2-5254008afee6','428ee192-8829-11ee-b6ec-080027b7463b','street_number'),
    ('1b622e58-0d0f-11ed-98c2-5254008afee6','1b624e60-0d0f-11ed-98c2-5254008afee6','street_name'),
    ('1b622e58-0d0f-11ed-98c2-5254008afee6','1b624082-0d0f-11ed-98c2-5254008afee6','city'),
    ('1b622e58-0d0f-11ed-98c2-5254008afee6','1b625414-0d0f-11ed-98c2-5254008afee6','postal_code'),
    ('1b622e58-0d0f-11ed-98c2-5254008afee6','a1032cd8-1a66-11ed-a3cf-5254008afee6','address_remarks'),
    ('1b622ab6-0d0f-11ed-98c2-5254008afee6','f5c343f3-217f-4ff0-a414-5dcaff74d2fa','pid'),
    ('1b622ab6-0d0f-11ed-98c2-5254008afee6','5513b739-04f5-4c98-9e6f-def560ff3555','pin'),
    ('1b622ab6-0d0f-11ed-98c2-5254008afee6','1b623ccc-0d0f-11ed-98c2-5254008afee6','legal_description'),
    ('1b622ab6-0d0f-11ed-98c2-5254008afee6','15656a28-1a67-11ed-b83c-5254008afee6','legal_address_remarks'),
    ('3083c10e-01c0-11f0-97f7-0242ac170007','4d3bb20c-01c0-11f0-97f7-0242ac170007','typology_class'),
    ('3083c10e-01c0-11f0-97f7-0242ac170007','e3f0d066-62d1-11f0-8725-76ff5c50888d','typology_remark'),
    ('0684fec8-0d07-11ed-8804-5254008afee6','167e3e88-98a3-11ee-a464-080027b7463b','bcap_submission_status'),
    ('0684fec8-0d07-11ed-8804-5254008afee6','dc974e68-8f0f-11ee-85a0-080027b7463b','restricted'),
    ('3ee73f28-ca40-11ed-af48-5254004d77d3','3ee73f28-ca40-11ed-af48-5254004d77d3','external_url'),
    ('3ee73f28-ca40-11ed-af48-5254004d77d3','1f5a7b92-ca41-11ed-933f-5254004d77d3','external_url_type'),
    ('1417996e-64ad-11f0-a4ef-6e5bb479055b','1417996e-64ad-11f0-a4ef-6e5bb479055b','restricted_ancestral_remains_remark'),
    ('1417996e-64ad-11f0-a4ef-6e5bb479055b','14179edc-64ad-11f0-a4ef-6e5bb479055b','remains_remark_made_by'),
    ('1417996e-64ad-11f0-a4ef-6e5bb479055b','1417a09e-64ad-11f0-a4ef-6e5bb479055b','remains_remark_entry_date'),
    ('dc827931-05ed-43e4-8da6-e99c0d02dae7','dc827931-05ed-43e4-8da6-e99c0d02dae7','remark_keyword'),
    ('05baebf6-61a5-11f0-9674-3a7a4e6803c5','05baf0e2-61a5-11f0-9674-3a7a4e6803c5','general_remark'),
    ('05baebf6-61a5-11f0-9674-3a7a4e6803c5','05baef2a-61a5-11f0-9674-3a7a4e6803c5','general_remark_source'),
    ('05baebf6-61a5-11f0-9674-3a7a4e6803c5','05baf01a-61a5-11f0-9674-3a7a4e6803c5','general_remark_date'),
    ('1bebc404-61a5-11f0-9674-3a7a4e6803c5','1bebc404-61a5-11f0-9674-3a7a4e6803c5','contravention_document'),
    ('250ed6fe-61a8-11f0-ad02-3a7a4e6803c5','250ed6fe-61a8-11f0-ad02-3a7a4e6803c5','restricted_document'),
    ('41fb5948-61a5-11f0-9674-3a7a4e6803c5','41fb5e20-61a5-11f0-9674-3a7a4e6803c5','inventory_remark'),
    ('41fb5948-61a5-11f0-9674-3a7a4e6803c5','41fb5eca-61a5-11f0-9674-3a7a4e6803c5','contravention_address'),
    ('41fb5948-61a5-11f0-9674-3a7a4e6803c5','41fb5f7e-61a5-11f0-9674-3a7a4e6803c5','contravention_pid'),
    ('41fb5948-61a5-11f0-9674-3a7a4e6803c5','41fb603c-61a5-11f0-9674-3a7a4e6803c5','nros_file_number'),
    ('b0ed31c4-61a4-11f0-9674-3a7a4e6803c5','b0ed366a-61a4-11f0-9674-3a7a4e6803c5','restricted_remark'),
    ('b0ed31c4-61a4-11f0-9674-3a7a4e6803c5','b0ed35ac-61a4-11f0-9674-3a7a4e6803c5','restricted_person'),
    ('b0ed31c4-61a4-11f0-9674-3a7a4e6803c5','b0ed34b2-61a4-11f0-9674-3a7a4e6803c5','restricted_entry_date'),
    ('c5159e8e-619f-11f0-acf4-3a7a4e6803c5','c515a668-619f-11f0-acf4-3a7a4e6803c5','conviction_details'),
    ('c5159e8e-619f-11f0-acf4-3a7a4e6803c5','c515a532-619f-11f0-acf4-3a7a4e6803c5','conviction_date'),
    ('2ad161ee-50ad-11f0-a6c8-0242ac170006','2ad161ee-50ad-11f0-a6c8-0242ac170006','related_site_documents'),
    ('2ad161ee-50ad-11f0-a6c8-0242ac170006','2ad16676-50ad-11f0-a6c8-0242ac170006','related_document_type'),
    ('2ad161ee-50ad-11f0-a6c8-0242ac170006','2ad1655e-50ad-11f0-a6c8-0242ac170006','related_document_description'),
    ('bb157a2a-01d8-11f0-850c-0242ac170007','bb157a2a-01d8-11f0-850c-0242ac170007','publication_reference'),
    ('c81626e8-01d8-11f0-850c-0242ac170007','c81626e8-01d8-11f0-850c-0242ac170007','site_images'),
    ('c81626e8-01d8-11f0-850c-0242ac170007','c8163160-01d8-11f0-850c-0242ac170007','primary_image'),
    ('c81626e8-01d8-11f0-850c-0242ac170007','c8162ad0-01d8-11f0-850c-0242ac170007','image_type'),
    ('c81626e8-01d8-11f0-850c-0242ac170007','c8162d0a-01d8-11f0-850c-0242ac170007','image_view'),
    ('c81626e8-01d8-11f0-850c-0242ac170007','c8162df0-01d8-11f0-850c-0242ac170007','image_description'),
    ('c81626e8-01d8-11f0-850c-0242ac170007','c816308e-01d8-11f0-850c-0242ac170007','image_features'),
    ('c81626e8-01d8-11f0-850c-0242ac170007','c8162c2e-01d8-11f0-850c-0242ac170007','photographer'),
    ('c81626e8-01d8-11f0-850c-0242ac170007','c8162ecc-01d8-11f0-850c-0242ac170007','copyright'),
    ('c81626e8-01d8-11f0-850c-0242ac170007','c8162fa8-01d8-11f0-850c-0242ac170007','image_date')
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
SELECT 'unprotected_areas' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '7c8eb1f8-44e2-4239-afaa-9cbf1fadf160'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = 'b18223c2-13ef-11f0-8695-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'site_alert' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '00e2b556-1979-11f0-8713-0242ac170008'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '034d1c32-13f2-11f0-9ff8-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'authority' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '034d1fac-13f2-11f0-9ff8-0242ac170007'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '034d1c32-13f2-11f0-9ff8-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'site_names' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = 'd60b1b28-35f4-11f0-afbc-0242ac170008'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '034d1c32-13f2-11f0-9ff8-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'site_decision' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = 'f80f08ae-1977-11f0-8713-0242ac170008'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '034d1c32-13f2-11f0-9ff8-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'biogeography' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '2509f4a2-197f-11f0-b2a5-0242ac170008'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '1b62393e-0d0f-11ed-98c2-5254008afee6'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'site_tenure' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '40a52cd0-197b-11f0-8d46-0242ac170008'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '1b62393e-0d0f-11ed-98c2-5254008afee6'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'site_tenure_remarks' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '4598a202-197c-11f0-b2a5-0242ac170008'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '40a52cd0-197b-11f0-8d46-0242ac170008'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'site_tenure_type' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '7b8991ec-197b-11f0-8d46-0242ac170008'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '40a52cd0-197b-11f0-8d46-0242ac170008'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'elevation' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = 'c2f9e970-01be-11f0-9078-0242ac170007'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '1b62393e-0d0f-11ed-98c2-5254008afee6'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'elevation_comments' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = 'bc131e78-01bf-11f0-97f7-0242ac170007'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = 'c2f9e970-01be-11f0-9078-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'bc_property_address' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '1b622e58-0d0f-11ed-98c2-5254008afee6'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '1b62393e-0d0f-11ed-98c2-5254008afee6'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'bc_property_legal_description' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '1b622ab6-0d0f-11ed-98c2-5254008afee6'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '1b622e58-0d0f-11ed-98c2-5254008afee6'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'site_typology' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '3083c10e-01c0-11f0-97f7-0242ac170007'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '09856d8c-01c0-11f0-97f7-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'restricted_ancestral_remains_remark' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '1417996e-64ad-11f0-a4ef-6e5bb479055b'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '14179ca2-64ad-11f0-a4ef-6e5bb479055b'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'remark_keyword' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = 'dc827931-05ed-43e4-8da6-e99c0d02dae7'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '75c91464-619f-11f0-acf4-3a7a4e6803c5'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'general_remark_information' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '05baebf6-61a5-11f0-9674-3a7a4e6803c5'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '75c91464-619f-11f0-acf4-3a7a4e6803c5'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'contravention_document' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '1bebc404-61a5-11f0-9674-3a7a4e6803c5'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '75c91464-619f-11f0-acf4-3a7a4e6803c5'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'restricted_document' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '250ed6fe-61a8-11f0-ad02-3a7a4e6803c5'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '75c91464-619f-11f0-acf4-3a7a4e6803c5'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'hca_contravention' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '41fb5948-61a5-11f0-9674-3a7a4e6803c5'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '75c91464-619f-11f0-acf4-3a7a4e6803c5'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'restricted_information' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = 'b0ed31c4-61a4-11f0-9674-3a7a4e6803c5'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '75c91464-619f-11f0-acf4-3a7a4e6803c5'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'conviction' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = 'c5159e8e-619f-11f0-acf4-3a7a4e6803c5'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '75c91464-619f-11f0-acf4-3a7a4e6803c5'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'related_site_documents' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = '2ad161ee-50ad-11f0-a6c8-0242ac170006'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '347e24f8-01d8-11f0-850c-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'publication_reference' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = 'bb157a2a-01d8-11f0-850c-0242ac170007'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '347e24f8-01d8-11f0-850c-0242ac170007'::uuid))
HAVING count(*) > 0
UNION ALL
SELECT 'site_images' AS child, count(*) AS orphans FROM public.tiles c
 WHERE c.nodegroupid = 'c81626e8-01d8-11f0-850c-0242ac170007'::uuid
   AND (c.parenttileid IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid
          AND p.nodegroupid = '347e24f8-01d8-11f0-850c-0242ac170007'::uuid))
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
SELECT 'site_boundary' AS node, ST_GeometryType(geom) AS geom_type, ST_SRID(geom) AS srid,
       count(*) AS n, count(*) FILTER (WHERE NOT ST_IsValid(geom)) AS invalid
FROM public.geojson_geometries WHERE nodeid = 'b18223c2-13ef-11f0-8695-0242ac170007'::uuid
GROUP BY 1,2,3 ORDER BY 4 DESC;

-- The specific invalid ones, with the reason. Fix these at source.
SELECT t.resourceinstanceid, g.tileid, ST_IsValidReason(ST_Transform(g.geom, 4326)) AS reason
FROM public.geojson_geometries g JOIN public.tiles t ON t.tileid = g.tileid
WHERE g.nodeid = 'b18223c2-13ef-11f0-8695-0242ac170007'::uuid AND NOT ST_IsValid(ST_Transform(g.geom, 4326))
LIMIT 50;

SELECT 'unprotected_areas' AS node, ST_GeometryType(geom) AS geom_type, ST_SRID(geom) AS srid,
       count(*) AS n, count(*) FILTER (WHERE NOT ST_IsValid(geom)) AS invalid
FROM public.geojson_geometries WHERE nodeid = '7c8eb1f8-44e2-4239-afaa-9cbf1fadf160'::uuid
GROUP BY 1,2,3 ORDER BY 4 DESC;

-- The specific invalid ones, with the reason. Fix these at source.
SELECT t.resourceinstanceid, g.tileid, ST_IsValidReason(ST_Transform(g.geom, 4326)) AS reason
FROM public.geojson_geometries g JOIN public.tiles t ON t.tileid = g.tileid
WHERE g.nodeid = '7c8eb1f8-44e2-4239-afaa-9cbf1fadf160'::uuid AND NOT ST_IsValid(ST_Transform(g.geom, 4326))
LIMIT 50;


-- =====================================================================
-- F. SCALE.  Sets the refresh budget.
-- =====================================================================
SELECT (SELECT count(*) FROM public.resource_instances WHERE graphid = 'cef9c510-e3e6-4057-ac08-89ad926180b4'::uuid) AS resources,
       (SELECT count(*) FROM public.tiles t JOIN public.resource_instances r
          USING (resourceinstanceid) WHERE r.graphid = 'cef9c510-e3e6-4057-ac08-89ad926180b4'::uuid)                  AS tiles;
