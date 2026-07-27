#!/usr/bin/env python3
import sys, importlib

S = importlib.import_module(sys.argv[1])
SC, SLUG = S.SCHEMA, S.SLUG
BY = {n[0]: n for n in S.NG}
GEOMS = [
    (n, f, nid)
    for n, ng, p, c, fl in S.NG
    for f, nid, dt, _ in fl
    if dt == "geojson-feature-collection"
]

o = [f"""-- =====================================================================
--  {SC} :: PREFLIGHT.  Run ALL of this and read the results BEFORE building.
--  Ordered by blast radius. A and C can change the DDL.
-- =====================================================================

-- =====================================================================
-- A. CARDINALITY.  THE LOAD-BEARING ASSUMPTION.
-- Every array-vs-object decision in the stack comes from this. Expected:"""]
for n, ng, p, c, fl in S.NG:
    o.append(f"--   {c:2}  {n:38} parent={p or '-'}")
o.append(
    f"""--
-- ANY disagreement -> fix {sys.argv[1]}.py and regenerate. Do not build and see.
SELECT n.name AS view_name, ng.cardinality, pn.name AS parent, ng.nodegroupid
FROM node_groups ng
JOIN nodes n              ON n.nodeid = ng.nodegroupid
LEFT JOIN node_groups png ON png.nodegroupid = ng.parentnodegroupid
LEFT JOIN nodes pn        ON pn.nodeid = png.nodegroupid
WHERE n.graphid = '{S.GRAPH_ID}'
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
         (SELECT count(*) FROM {SC}.instances),
         (SELECT count(*) FROM public.resource_instances WHERE graphid = '{S.GRAPH_ID}'::uuid)"""
)
for n, ng, p, c, fl in S.NG:
    o.append(
        f"  UNION ALL SELECT '{n}',\n"
        f"         (SELECT count(*) FROM {SC}.{n}),\n"
        f"         (SELECT count(*) FROM public.tiles WHERE nodegroupid = '{ng}'::uuid)"
    )
o.append(""") x(view_name, via_view, via_tiles)
ORDER BY verdict DESC, view_name;


-- =====================================================================
-- C. NODE UUID SANITY.  A mistyped uuid does NOT error - tiledata -> '<wrong>'
-- just returns NULL, and you ship a permanently-empty column. Expect
-- node_exists = true on EVERY row.
-- =====================================================================
WITH used(ng, nodeid, alias) AS (VALUES""")
rows = [
    f"    ('{ng}','{nid}','{f}')" for n, ng, p, c, fl in S.NG for f, nid, dt, _ in fl
]
o.append(",\n".join(rows))
o.append(f""")
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
-- =====================================================================""")
for n, ng, p, c, fl in S.NG:
    if p:
        o.append(
            f"SELECT '{n}' AS child, count(*) AS orphans FROM public.tiles c\n"
            f" WHERE c.nodegroupid = '{ng}'::uuid\n"
            f"   AND (c.parenttileid IS NULL OR NOT EXISTS (\n"
            f"        SELECT 1 FROM public.tiles p WHERE p.tileid = c.parenttileid\n"
            f"          AND p.nodegroupid = '{BY[p][1]}'::uuid))\n"
            f"HAVING count(*) > 0\nUNION ALL"
        )
o.append("SELECT 'none', 0 WHERE false;\n")
if GEOMS:
    o.append("""
-- =====================================================================
-- E. GEOMETRY.  Source is SRID 3857 (Web Mercator); the stack transforms to 4326
-- and the ::geometry(...,4326) casts ENFORCE it.
-- Invalid geometries are REPAIRED with ST_MakeValid so one bad polygon cannot
-- break every downstream spatial query - but repair CHANGES an authoritative
-- boundary (a bowtie becomes two polygons). Fix them at source. This finds them.
-- =====================================================================""")
    for n, f, nid in GEOMS:
        o.append(
            f"""SELECT '{f}' AS node, ST_GeometryType(geom) AS geom_type, ST_SRID(geom) AS srid,
       count(*) AS n, count(*) FILTER (WHERE NOT ST_IsValid(geom)) AS invalid
FROM public.geojson_geometries WHERE nodeid = '{nid}'::uuid
GROUP BY 1,2,3 ORDER BY 4 DESC;

-- The specific invalid ones, with the reason. Fix these at source.
SELECT t.resourceinstanceid, g.tileid, ST_IsValidReason(ST_Transform(g.geom, 4326)) AS reason
FROM public.geojson_geometries g JOIN public.tiles t ON t.tileid = g.tileid
WHERE g.nodeid = '{nid}'::uuid AND NOT ST_IsValid(ST_Transform(g.geom, 4326))
LIMIT 50;
"""
        )
o.append("""
-- =====================================================================
-- F. SCALE.  Sets the refresh budget.
-- =====================================================================
SELECT (SELECT count(*) FROM public.resource_instances WHERE graphid = '%s'::uuid) AS resources,
       (SELECT count(*) FROM public.tiles t JOIN public.resource_instances r
          USING (resourceinstanceid) WHERE r.graphid = '%s'::uuid)                  AS tiles;
""" % (S.GRAPH_ID, S.GRAPH_ID))
open(f"{SLUG}_01_preflight.sql", "w").write("\n".join(o))
print(f"{SLUG}_01_preflight.sql")
