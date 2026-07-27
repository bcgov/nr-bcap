-- Alignment regression test. Run after every build. EXPECT ZERO ROWS.
-- Not a schema object - run manually to verify correctness.
--
-- Every sibling column from one cardinality-n nodegroup must have exactly
-- <nodegroup>_count slots. A mismatch means a null element got SKIPPED.
-- =====================================================================
WITH v AS (
  SELECT resourceinstanceid, information_carrier_count AS n, 'resource_flat_v1.information_carrier' AS grp,
         ARRAY[arches_util.nslots(information_carrier),
               arches_util.nslots(information_carrier_file_ids)] AS slots,
         ARRAY['information_carrier', 'information_carrier_file_ids']::text[] AS colnames
  FROM publication.mv_resource_flat_v1 WHERE information_carrier_count > 0
  UNION ALL
  SELECT resourceinstanceid, keyword_count AS n, 'resource_flat_v1.keyword' AS grp,
         ARRAY[arches_util.nslots(keyword),
               arches_util.nslots(keyword_ids)] AS slots,
         ARRAY['keyword', 'keyword_ids']::text[] AS colnames
  FROM publication.mv_resource_flat_v1 WHERE keyword_count > 0
  UNION ALL
  SELECT resourceinstanceid, authors_count AS n, 'resource_flat_v1.authors' AS grp,
         ARRAY[arches_util.nslots(other_authors_unlisted),
               arches_util.nslots(authors),
               arches_util.nslots(authors_ids)] AS slots,
         ARRAY['other_authors_unlisted', 'authors', 'authors_ids']::text[] AS colnames
  FROM publication.mv_resource_flat_v1 WHERE authors_count > 0
  UNION ALL
  SELECT resourceinstanceid, publication_identifier_count AS n, 'resource_flat_v1.publication_identifier' AS grp,
         ARRAY[arches_util.nslots(publication_identifier_type),
               arches_util.nslots(publication_identifier_type_ids),
               arches_util.nslots(publication_identifier)] AS slots,
         ARRAY['publication_identifier_type', 'publication_identifier_type_ids', 'publication_identifier']::text[] AS colnames
  FROM publication.mv_resource_flat_v1 WHERE publication_identifier_count > 0
)
SELECT grp, colname,
       count(DISTINCT resourceinstanceid) AS rows_affected,
       count(*)                           AS bad_cells
FROM v, LATERAL unnest(slots, colnames) AS u(sl, colname)
WHERE sl IS DISTINCT FROM n
GROUP BY grp, colname
ORDER BY rows_affected DESC, grp, colname;
