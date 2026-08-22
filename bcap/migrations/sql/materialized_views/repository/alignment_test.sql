-- Alignment regression test. EXPECT ZERO ROWS.
-- Run manually after a full generate + refresh.

WITH v AS (
  SELECT resourceinstanceid, repository_notes_count AS n, 'resource_flat_v1.repository_notes' AS grp,
         ARRAY[arches_util.nslots(note)] AS slots,
         ARRAY['note']::text[] AS colnames
  FROM repository.mv_resource_flat_v1 WHERE repository_notes_count > 0
  UNION ALL
  SELECT resourceinstanceid, alternate_identifiers_count AS n, 'resource_flat_v1.alternate_identifiers' AS grp,
         ARRAY[arches_util.nslots(alternate_name),
               arches_util.nslots(alternate_code)] AS slots,
         ARRAY['alternate_name', 'alternate_code']::text[] AS colnames
  FROM repository.mv_resource_flat_v1 WHERE alternate_identifiers_count > 0
)
SELECT grp, colname,
       count(DISTINCT resourceinstanceid) AS rows_affected,
       count(*)                           AS bad_cells
FROM v, LATERAL unnest(slots, colnames) AS u(sl, colname)
WHERE sl IS DISTINCT FROM n
GROUP BY grp, colname
ORDER BY rows_affected DESC, grp, colname;
