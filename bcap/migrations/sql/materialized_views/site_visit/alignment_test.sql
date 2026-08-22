-- Alignment regression test. EXPECT ZERO ROWS.
-- Run manually after a full generate + refresh.

WITH v AS (
  SELECT resourceinstanceid, ancestral_remains_count AS n, 'resource_flat_v1.ancestral_remains' AS grp,
         ARRAY[arches_util.nslots(ancestral_remains_type),
               arches_util.nslots(ancestral_remains_type_ids),
               arches_util.nslots(multiple_burials),
               arches_util.nslots(ancestral_remains_status),
               arches_util.nslots(ancestral_remains_status_ids),
               arches_util.nslots(ancestral_remains_remarks),
               arches_util.nslots(minimum_number_of_individuals),
               arches_util.nslots(ancestral_remains_repository),
               arches_util.nslots(ancestral_remains_repository_ids)] AS slots,
         ARRAY['ancestral_remains_type', 'ancestral_remains_type_ids', 'multiple_burials', 'ancestral_remains_status', 'ancestral_remains_status_ids', 'ancestral_remains_remarks', 'minimum_number_of_individuals', 'ancestral_remains_repository', 'ancestral_remains_repository_ids']::text[] AS colnames
  FROM site_visit.mv_resource_flat_v1 WHERE ancestral_remains_count > 0
  UNION ALL
  SELECT resourceinstanceid, related_site_documents_count AS n, 'resource_flat_v1.related_site_documents' AS grp,
         ARRAY[arches_util.nslots(related_document_description),
               arches_util.nslots(related_document_type),
               arches_util.nslots(related_document_type_ids),
               arches_util.nslots(related_site_documents),
               arches_util.nslots(related_site_documents_file_ids)] AS slots,
         ARRAY['related_document_description', 'related_document_type', 'related_document_type_ids', 'related_site_documents', 'related_site_documents_file_ids']::text[] AS colnames
  FROM site_visit.mv_resource_flat_v1 WHERE related_site_documents_count > 0
  UNION ALL
  SELECT resourceinstanceid, publication_reference_count AS n, 'resource_flat_v1.publication_reference' AS grp,
         ARRAY[arches_util.nslots(publication_reference),
               arches_util.nslots(publication_reference_ids)] AS slots,
         ARRAY['publication_reference', 'publication_reference_ids']::text[] AS colnames
  FROM site_visit.mv_resource_flat_v1 WHERE publication_reference_count > 0
  UNION ALL
  SELECT resourceinstanceid, site_images_count AS n, 'resource_flat_v1.site_images' AS grp,
         ARRAY[arches_util.nslots(primary_image),
               arches_util.nslots(image_type),
               arches_util.nslots(image_type_ids),
               arches_util.nslots(site_images),
               arches_util.nslots(site_images_file_ids),
               arches_util.nslots(photographer),
               arches_util.nslots(image_view),
               arches_util.nslots(image_view_ids),
               arches_util.nslots(image_description),
               arches_util.nslots(copyright),
               arches_util.nslots(image_date),
               arches_util.nslots(image_features)] AS slots,
         ARRAY['primary_image', 'image_type', 'image_type_ids', 'site_images', 'site_images_file_ids', 'photographer', 'image_view', 'image_view_ids', 'image_description', 'copyright', 'image_date', 'image_features']::text[] AS colnames
  FROM site_visit.mv_resource_flat_v1 WHERE site_images_count > 0
  UNION ALL
  SELECT resourceinstanceid, recommendation_count AS n, 'resource_flat_v1.recommendation' AS grp,
         ARRAY[arches_util.nslots(recorders_recommendation),
               arches_util.nslots(archaeology_branch_recommendation)] AS slots,
         ARRAY['recorders_recommendation', 'archaeology_branch_recommendation']::text[] AS colnames
  FROM site_visit.mv_resource_flat_v1 WHERE recommendation_count > 0
  UNION ALL
  SELECT resourceinstanceid, general_remark_count AS n, 'resource_flat_v1.general_remark' AS grp,
         ARRAY[arches_util.nslots(remark_source),
               arches_util.nslots(remark_source_ids),
               arches_util.nslots(remark_date),
               arches_util.nslots(remark)] AS slots,
         ARRAY['remark_source', 'remark_source_ids', 'remark_date', 'remark']::text[] AS colnames
  FROM site_visit.mv_resource_flat_v1 WHERE general_remark_count > 0
  UNION ALL
  SELECT resourceinstanceid, new_site_names_count AS n, 'resource_flat_v1.new_site_names' AS grp,
         ARRAY[arches_util.nslots(name),
               arches_util.nslots(assigned_or_reported_by),
               arches_util.nslots(assigned_or_reported_by_ids),
               arches_util.nslots(name_type),
               arches_util.nslots(name_type_ids),
               arches_util.nslots(name_remarks),
               arches_util.nslots(assigned_or_reported_date)] AS slots,
         ARRAY['name', 'assigned_or_reported_by', 'assigned_or_reported_by_ids', 'name_type', 'name_type_ids', 'name_remarks', 'assigned_or_reported_date']::text[] AS colnames
  FROM site_visit.mv_resource_flat_v1 WHERE new_site_names_count > 0
  UNION ALL
  SELECT resourceinstanceid, archaeological_culture_count AS n, 'resource_flat_v1.archaeological_culture' AS grp,
         ARRAY[arches_util.nslots(culture_remarks),
               arches_util.nslots(archaeological_culture),
               arches_util.nslots(archaeological_culture_ids)] AS slots,
         ARRAY['culture_remarks', 'archaeological_culture', 'archaeological_culture_ids']::text[] AS colnames
  FROM site_visit.mv_resource_flat_v1 WHERE archaeological_culture_count > 0
  UNION ALL
  SELECT resourceinstanceid, stratigraphy_count AS n, 'resource_flat_v1.stratigraphy' AS grp,
         ARRAY[arches_util.nslots(stratigraphy)] AS slots,
         ARRAY['stratigraphy']::text[] AS colnames
  FROM site_visit.mv_resource_flat_v1 WHERE stratigraphy_count > 0
  UNION ALL
  SELECT resourceinstanceid, additional_site_typology_count AS n, 'resource_flat_v1.additional_site_typology' AS grp,
         ARRAY[arches_util.nslots(typology_class),
               arches_util.nslots(typology_class_ids),
               arches_util.nslots(typology_remark)] AS slots,
         ARRAY['typology_class', 'typology_class_ids', 'typology_remark']::text[] AS colnames
  FROM site_visit.mv_resource_flat_v1 WHERE additional_site_typology_count > 0
  UNION ALL
  SELECT resourceinstanceid, site_disturbance_count AS n, 'resource_flat_v1.site_disturbance' AS grp,
         ARRAY[arches_util.nslots(disturbance_period),
               arches_util.nslots(disturbance_period_ids),
               arches_util.nslots(disturbance_cause),
               arches_util.nslots(disturbance_cause_ids),
               arches_util.nslots(disturbance_remarks)] AS slots,
         ARRAY['disturbance_period', 'disturbance_period_ids', 'disturbance_cause', 'disturbance_cause_ids', 'disturbance_remarks']::text[] AS colnames
  FROM site_visit.mv_resource_flat_v1 WHERE site_disturbance_count > 0
  UNION ALL
  SELECT resourceinstanceid, chronology_count AS n, 'resource_flat_v1.chronology' AS grp,
         ARRAY[arches_util.nslots(end_year_qualifier),
               arches_util.nslots(end_year_qualifier_ids),
               arches_util.nslots(end_year_calendar),
               arches_util.nslots(end_year_calendar_ids),
               arches_util.nslots(chronology_remarks),
               arches_util.nslots(determination_method),
               arches_util.nslots(determination_method_ids),
               arches_util.nslots(start_year),
               arches_util.nslots(information_source),
               arches_util.nslots(end_year),
               arches_util.nslots(start_year_calendar),
               arches_util.nslots(start_year_calendar_ids),
               arches_util.nslots(start_year_qualifier),
               arches_util.nslots(start_year_qualifier_ids)] AS slots,
         ARRAY['end_year_qualifier', 'end_year_qualifier_ids', 'end_year_calendar', 'end_year_calendar_ids', 'chronology_remarks', 'determination_method', 'determination_method_ids', 'start_year', 'information_source', 'end_year', 'start_year_calendar', 'start_year_calendar_ids', 'start_year_qualifier', 'start_year_qualifier_ids']::text[] AS colnames
  FROM site_visit.mv_resource_flat_v1 WHERE chronology_count > 0
  UNION ALL
  SELECT resourceinstanceid, cultural_material_count AS n, 'resource_flat_v1.cultural_material' AS grp,
         ARRAY[arches_util.nslots(cultural_material_type),
               arches_util.nslots(cultural_material_type_ids),
               arches_util.nslots(cultural_material_status),
               arches_util.nslots(cultural_material_status_ids),
               arches_util.nslots(cultural_material_details),
               arches_util.nslots(number_of_artifacts),
               arches_util.nslots(repository),
               arches_util.nslots(repository_ids)] AS slots,
         ARRAY['cultural_material_type', 'cultural_material_type_ids', 'cultural_material_status', 'cultural_material_status_ids', 'cultural_material_details', 'number_of_artifacts', 'repository', 'repository_ids']::text[] AS colnames
  FROM site_visit.mv_resource_flat_v1 WHERE cultural_material_count > 0
  UNION ALL
  SELECT resourceinstanceid, archaeological_feature_count AS n, 'resource_flat_v1.archaeological_feature' AS grp,
         ARRAY[arches_util.nslots(feature_count),
               arches_util.nslots(archaeological_feature),
               arches_util.nslots(archaeological_feature_ids),
               arches_util.nslots(feature_remarks)] AS slots,
         ARRAY['feature_count', 'archaeological_feature', 'archaeological_feature_ids', 'feature_remarks']::text[] AS colnames
  FROM site_visit.mv_resource_flat_v1 WHERE archaeological_feature_count > 0
  UNION ALL
  SELECT resourceinstanceid, team_member_count AS n, 'resource_flat_v1.team_member' AS grp,
         ARRAY[arches_util.nslots(was_on_site),
               arches_util.nslots(team_member),
               arches_util.nslots(team_member_ids),
               arches_util.nslots(member_roles),
               arches_util.nslots(member_roles_ids)] AS slots,
         ARRAY['was_on_site', 'team_member', 'team_member_ids', 'member_roles', 'member_roles_ids']::text[] AS colnames
  FROM site_visit.mv_resource_flat_v1 WHERE team_member_count > 0
  UNION ALL
  SELECT resourceinstanceid, biogeography_count AS n, 'site_visit_location_flat_v1.biogeography' AS grp,
         ARRAY[arches_util.nslots(biogeography_description),
               arches_util.nslots(biogeography_type),
               arches_util.nslots(biogeography_type_ids),
               arches_util.nslots(biogeography_name)] AS slots,
         ARRAY['biogeography_description', 'biogeography_type', 'biogeography_type_ids', 'biogeography_name']::text[] AS colnames
  FROM site_visit.mv_site_visit_location_flat_v1 WHERE biogeography_count > 0
)
SELECT grp, colname,
       count(DISTINCT resourceinstanceid) AS rows_affected,
       count(*)                           AS bad_cells
FROM v, LATERAL unnest(slots, colnames) AS u(sl, colname)
WHERE sl IS DISTINCT FROM n
GROUP BY grp, colname
ORDER BY rows_affected DESC, grp, colname;
