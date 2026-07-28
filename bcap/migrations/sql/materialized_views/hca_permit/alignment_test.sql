-- Alignment regression test. Run after every build. EXPECT ZERO ROWS.
-- Not a schema object - run manually to verify correctness.
--
-- Every sibling column from one cardinality-n nodegroup must have exactly
-- <nodegroup>_count slots. A mismatch means a null element got SKIPPED.
-- =====================================================================
WITH v AS (

)
SELECT grp, colname,
       count(DISTINCT resourceinstanceid) AS rows_affected,
       count(*)                           AS bad_cells
FROM v, LATERAL unnest(slots, colnames) AS u(sl, colname)
WHERE sl IS DISTINCT FROM n
GROUP BY grp, colname
ORDER BY rows_affected DESC, grp, colname;
