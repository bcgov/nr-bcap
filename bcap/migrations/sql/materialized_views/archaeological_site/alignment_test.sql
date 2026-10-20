-- Alignment regression test. EXPECT ZERO ROWS.
-- Run manually after a full generate + refresh.

WITH v AS (
  SELECT resourceinstanceid, site_record_admin_count AS n, 'resource_flat.site_record_admin' AS grp,
         ARRAY[arches_util.nslots(bcap_submission_status),
               arches_util.nslots(bcap_submission_status_ids),
               arches_util.nslots(restricted)] AS slots,
         ARRAY['bcap_submission_status', 'bcap_submission_status_ids', 'restricted']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE site_record_admin_count > 0
  UNION ALL
  SELECT resourceinstanceid, external_url_count AS n, 'resource_flat.external_url' AS grp,
         ARRAY[arches_util.nslots(external_url_type),
               arches_util.nslots(external_url_type_ids),
               arches_util.nslots(external_url),
               arches_util.nslots(external_url_label)] AS slots,
         ARRAY['external_url_type', 'external_url_type_ids', 'external_url', 'external_url_label']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE external_url_count > 0
  UNION ALL
  SELECT resourceinstanceid, unprotected_area_count AS n, 'resource_flat.unprotected_area' AS grp,
         ARRAY[arches_util.nslots(unprotected_site_area_rationale),
               arches_util.nslots(unprotected_site_area_type),
               arches_util.nslots(unprotected_site_area_type_ids),
               arches_util.nslots(unprotected_site_area_criteria),
               arches_util.nslots(unprotected_site_area_criteria_ids)] AS slots,
         ARRAY['unprotected_site_area_rationale', 'unprotected_site_area_type', 'unprotected_site_area_type_ids', 'unprotected_site_area_criteria', 'unprotected_site_area_criteria_ids']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE unprotected_area_count > 0
  UNION ALL
  SELECT resourceinstanceid, site_typology_count AS n, 'resource_flat.site_typology' AS grp,
         ARRAY[arches_util.nslots(typology_class),
               arches_util.nslots(typology_class_ids),
               arches_util.nslots(typology_remark)] AS slots,
         ARRAY['typology_class', 'typology_class_ids', 'typology_remark']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE site_typology_count > 0
  UNION ALL
  SELECT resourceinstanceid, site_decision_count AS n, 'resource_flat.site_decision' AS grp,
         ARRAY[arches_util.nslots(decision_registration_status),
               arches_util.nslots(decision_registration_status_ids),
               arches_util.nslots(decision_date),
               arches_util.nslots(decision_made_by),
               arches_util.nslots(decision_made_by_ids),
               arches_util.nslots(recommended_by),
               arches_util.nslots(recommended_by_ids),
               arches_util.nslots(recommendation_date),
               arches_util.nslots(decision_description),
               arches_util.nslots(site_decision),
               arches_util.nslots(site_decision_ids)] AS slots,
         ARRAY['decision_registration_status', 'decision_registration_status_ids', 'decision_date', 'decision_made_by', 'decision_made_by_ids', 'recommended_by', 'recommended_by_ids', 'recommendation_date', 'decision_description', 'site_decision', 'site_decision_ids']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE site_decision_count > 0
  UNION ALL
  SELECT resourceinstanceid, site_names_count AS n, 'resource_flat.site_names' AS grp,
         ARRAY[arches_util.nslots(name),
               arches_util.nslots(assigned_or_reported_by),
               arches_util.nslots(assigned_or_reported_by_ids),
               arches_util.nslots(name_type),
               arches_util.nslots(name_type_ids),
               arches_util.nslots(name_remarks),
               arches_util.nslots(assigned_or_reported_date)] AS slots,
         ARRAY['name', 'assigned_or_reported_by', 'assigned_or_reported_by_ids', 'name_type', 'name_type_ids', 'name_remarks', 'assigned_or_reported_date']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE site_names_count > 0
  UNION ALL
  SELECT resourceinstanceid, authority_count AS n, 'resource_flat.authority' AS grp,
         ARRAY[arches_util.nslots(authority_start_date),
               arches_util.nslots(authority_end_date),
               arches_util.nslots(legislative_act),
               arches_util.nslots(legislative_act_ids),
               arches_util.nslots(authority_protection_type),
               arches_util.nslots(authority_protection_type_ids),
               arches_util.nslots(reference_number),
               arches_util.nslots(authority_description)] AS slots,
         ARRAY['authority_start_date', 'authority_end_date', 'legislative_act', 'legislative_act_ids', 'authority_protection_type', 'authority_protection_type_ids', 'reference_number', 'authority_description']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE authority_count > 0
  UNION ALL
  SELECT resourceinstanceid, remark_keyword_count AS n, 'resource_flat.remark_keyword' AS grp,
         ARRAY[arches_util.nslots(remark_keyword)] AS slots,
         ARRAY['remark_keyword']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE remark_keyword_count > 0
  UNION ALL
  SELECT resourceinstanceid, restricted_document_count AS n, 'resource_flat.restricted_document' AS grp,
         ARRAY[arches_util.nslots(restricted_document),
               arches_util.nslots(restricted_document_file_ids),
               arches_util.nslots(restricted_document_file_paths)] AS slots,
         ARRAY['restricted_document', 'restricted_document_file_ids', 'restricted_document_file_paths']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE restricted_document_count > 0
  UNION ALL
  SELECT resourceinstanceid, hca_contravention_count AS n, 'resource_flat.hca_contravention' AS grp,
         ARRAY[arches_util.nslots(inventory_remark),
               arches_util.nslots(contravention_address),
               arches_util.nslots(contravention_pid),
               arches_util.nslots(nros_file_number)] AS slots,
         ARRAY['inventory_remark', 'contravention_address', 'contravention_pid', 'nros_file_number']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE hca_contravention_count > 0
  UNION ALL
  SELECT resourceinstanceid, contravention_document_count AS n, 'resource_flat.contravention_document' AS grp,
         ARRAY[arches_util.nslots(contravention_document),
               arches_util.nslots(contravention_document_file_ids),
               arches_util.nslots(contravention_document_file_paths)] AS slots,
         ARRAY['contravention_document', 'contravention_document_file_ids', 'contravention_document_file_paths']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE contravention_document_count > 0
  UNION ALL
  SELECT resourceinstanceid, restricted_information_count AS n, 'resource_flat.restricted_information' AS grp,
         ARRAY[arches_util.nslots(restricted_entry_date),
               arches_util.nslots(restricted_person),
               arches_util.nslots(restricted_person_ids),
               arches_util.nslots(restricted_remark)] AS slots,
         ARRAY['restricted_entry_date', 'restricted_person', 'restricted_person_ids', 'restricted_remark']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE restricted_information_count > 0
  UNION ALL
  SELECT resourceinstanceid, general_remark_information_count AS n, 'resource_flat.general_remark_information' AS grp,
         ARRAY[arches_util.nslots(general_remark_source),
               arches_util.nslots(general_remark_source_ids),
               arches_util.nslots(general_remark_date),
               arches_util.nslots(general_remark)] AS slots,
         ARRAY['general_remark_source', 'general_remark_source_ids', 'general_remark_date', 'general_remark']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE general_remark_information_count > 0
  UNION ALL
  SELECT resourceinstanceid, conviction_count AS n, 'resource_flat.conviction' AS grp,
         ARRAY[arches_util.nslots(conviction_date),
               arches_util.nslots(conviction_details)] AS slots,
         ARRAY['conviction_date', 'conviction_details']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE conviction_count > 0
  UNION ALL
  SELECT resourceinstanceid, related_site_documents_count AS n, 'resource_flat.related_site_documents' AS grp,
         ARRAY[arches_util.nslots(related_document_description),
               arches_util.nslots(related_document_type),
               arches_util.nslots(related_document_type_ids),
               arches_util.nslots(related_site_documents),
               arches_util.nslots(related_site_documents_file_ids),
               arches_util.nslots(related_site_documents_file_paths)] AS slots,
         ARRAY['related_document_description', 'related_document_type', 'related_document_type_ids', 'related_site_documents', 'related_site_documents_file_ids', 'related_site_documents_file_paths']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE related_site_documents_count > 0
  UNION ALL
  SELECT resourceinstanceid, site_images_count AS n, 'resource_flat.site_images' AS grp,
         ARRAY[arches_util.nslots(image_type),
               arches_util.nslots(image_type_ids),
               arches_util.nslots(photographer),
               arches_util.nslots(site_images),
               arches_util.nslots(site_images_file_ids),
               arches_util.nslots(site_images_file_paths),
               arches_util.nslots(image_view),
               arches_util.nslots(image_view_ids),
               arches_util.nslots(image_description),
               arches_util.nslots(copyright),
               arches_util.nslots(image_date),
               arches_util.nslots(image_features),
               arches_util.nslots(primary_image)] AS slots,
         ARRAY['image_type', 'image_type_ids', 'photographer', 'site_images', 'site_images_file_ids', 'site_images_file_paths', 'image_view', 'image_view_ids', 'image_description', 'copyright', 'image_date', 'image_features', 'primary_image']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE site_images_count > 0
  UNION ALL
  SELECT resourceinstanceid, publication_reference_count AS n, 'resource_flat.publication_reference' AS grp,
         ARRAY[arches_util.nslots(publication_reference),
               arches_util.nslots(publication_reference_ids)] AS slots,
         ARRAY['publication_reference', 'publication_reference_ids']::text[] AS colnames
  FROM archaeological_site.mv_resource_flat WHERE publication_reference_count > 0
  UNION ALL
  SELECT resourceinstanceid, biogeography_count AS n, 'site_location_flat.biogeography' AS grp,
         ARRAY[arches_util.nslots(biogeography_type),
               arches_util.nslots(biogeography_type_ids),
               arches_util.nslots(biogeography_description),
               arches_util.nslots(biogeography_name)] AS slots,
         ARRAY['biogeography_type', 'biogeography_type_ids', 'biogeography_description', 'biogeography_name']::text[] AS colnames
  FROM archaeological_site.mv_site_location_flat WHERE biogeography_count > 0
  UNION ALL
  SELECT resourceinstanceid, elevation_comments_count AS n, 'site_location_flat.elevation_comments' AS grp,
         ARRAY[arches_util.nslots(elevation_comments)] AS slots,
         ARRAY['elevation_comments']::text[] AS colnames
  FROM archaeological_site.mv_site_location_flat WHERE elevation_comments_count > 0
  UNION ALL
  SELECT resourceinstanceid, bc_property_legal_description_count AS n, 'bc_property_address_flat.bc_property_legal_description' AS grp,
         ARRAY[arches_util.nslots(pid),
               arches_util.nslots(pin),
               arches_util.nslots(legal_description),
               arches_util.nslots(legal_address_remarks)] AS slots,
         ARRAY['pid', 'pin', 'legal_description', 'legal_address_remarks']::text[] AS colnames
  FROM archaeological_site.mv_bc_property_address_flat WHERE bc_property_legal_description_count > 0
)
SELECT grp, colname,
       count(DISTINCT resourceinstanceid) AS rows_affected,
       count(*)                           AS bad_cells
FROM v, LATERAL unnest(slots, colnames) AS u(sl, colname)
WHERE sl IS DISTINCT FROM n
GROUP BY grp, colname
ORDER BY rows_affected DESC, grp, colname;
