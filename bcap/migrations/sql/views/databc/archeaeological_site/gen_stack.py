#!/usr/bin/env python3
import as_spec as S
from collections import defaultdict

BY = {n[0]: n for n in S.NG}
KIDS = defaultdict(list)
for n in S.NG:
    if n[2]:
        KIDS[n[2]].append(n[0])
TOPS = [n[0] for n in S.NG if n[2] is None]


def card(n):
    return BY[n][3]


def ngid(n):
    return BY[n][1]


def fields(n):
    return BY[n][4]


def chain(n):
    """path from top-level branch down to n, inclusive"""
    c = []
    while n:
        c.append(n)
        n = BY[n][2]
    return list(reversed(c))


def geom_field(n):
    for f, nid, dt, _ in fields(n):
        if dt == "geojson-feature-collection":
            return f, nid
    return None


# ---------- value decoding, tiles-direct ----------
def decode(f, nid, dt, fmt, t="t"):
    if dt in ("string",):
        return f"arches_util.i18n_text({t}.tiledata -> '{nid}')"
    if dt in ("non-localized-string", "borden-number-datatype"):
        return f"{t}.tiledata ->> '{nid}'"
    if dt == "reference":
        return f"arches_util.reference_flat({t}.tiledata -> '{nid}')"
    if dt == "resource-instance":
        return f"arches_util.resource_id({t}.tiledata -> '{nid}')"
    if dt == "resource-instance-list":
        return f"arches_util.resource_ids({t}.tiledata -> '{nid}')"
    if dt == "file-list":
        return f"arches_util.file_list({t}.tiledata -> '{nid}')"
    if dt == "url":
        return f"arches_util.url_obj({t}.tiledata -> '{nid}')"
    if dt == "number":
        return f"NULLIF({t}.tiledata ->> '{nid}', '')::numeric"
    if dt == "boolean":
        return f"NULLIF({t}.tiledata ->> '{nid}', '')::boolean"
    if dt == "date":
        return f"to_date(NULLIF({t}.tiledata ->> '{nid}', ''), '{fmt}')"
    raise ValueError(dt)


ORD = "COALESCE(t.sortorder, 2147483647), t.tileid"


def obj_expr(n, indent):
    """jsonb_build_object for one tile of nodegroup n, including child keys"""
    pad = " " * indent
    parts = []
    g = geom_field(n)
    for f, nid, dt, fmt in fields(n):
        if dt == "geojson-feature-collection":
            parts.append(
                f"'{f}', CASE WHEN g.geom IS NULL THEN NULL "
                f"ELSE ST_AsGeoJSON(g.geom, 7)::jsonb END"
            )
        else:
            parts.append(f"'{f}', {decode(f, nid, dt, fmt)}")
    for k in KIDS[n]:
        if card(k) == "n":
            parts.append(f"'{k}', COALESCE({k}.arr, '[]'::jsonb)")
        else:
            parts.append(f"'{k}', {k}.obj")
    body = (",\n" + pad + "    ").join(parts)
    return f"jsonb_build_object(\n{pad}    {body}\n{pad})"


def cte(n):
    """emit the CTE for nodegroup n (children must already be emitted)"""
    g = geom_field(n)
    joins = []
    if g:
        joins.append(f"    LEFT JOIN geom_{n} g ON g.tileid = t.tileid")
    for k in KIDS[n]:
        joins.append(f"    LEFT JOIN {k} {k} ON {k}.parenttileid = t.tileid")
    j = ("\n" + "\n".join(joins)) if joins else ""

    top = BY[n][2] is None
    key = "t.resourceinstanceid" if top else "t.parenttileid"
    keyname = "resourceinstanceid" if top else "parenttileid"
    o = obj_expr(n, 8)

    if card(n) == "n":
        return (
            f"{n} AS (\n"
            f"    SELECT {key} AS {keyname},\n"
            f"           jsonb_agg({o} ORDER BY {ORD}) AS arr\n"
            f"    FROM public.tiles t{j}\n"
            f"    WHERE t.nodegroupid = '{ngid(n)}'::uuid\n"
            f"    GROUP BY {key}\n)"
        )
    return (
        f"{n} AS (\n"
        f"    SELECT DISTINCT ON ({key}) {key} AS {keyname},\n"
        f"           {o} AS obj\n"
        f"    FROM public.tiles t{j}\n"
        f"    WHERE t.nodegroupid = '{ngid(n)}'::uuid\n"
        f"    ORDER BY {key}, {ORD}\n)"
    )


def geom_cte(n):
    g = geom_field(n)
    if not g:
        return None
    f, nid = g
    return (
        f"geom_{n} AS (\n"
        f"    SELECT gg.tileid, ST_Collect(ST_Transform(gg.geom, 4326)) AS geom\n"
        f"    FROM public.geojson_geometries gg\n"
        f"    WHERE gg.nodeid = '{nid}'::uuid\n"
        f"    GROUP BY gg.tileid\n)"
    )


def subtree(n):
    """post-order: children first"""
    out = []
    for k in KIDS[n]:
        out += subtree(k)
    gc = geom_cte(n)
    if gc:
        out.append(gc)
    out.append(cte(n))
    return out


# ---------------- branch matviews ----------------
def branch_mv(n):
    ctes = subtree(n)
    # the top nodegroup's own CTE is last; select from it
    body = ",\n".join(ctes)
    geoms = [x for x in [n] + [k for k in KIDS[n]] if geom_field(x)]
    extra = ""
    if card(n) == "n":
        sel = f"SELECT resourceinstanceid, arr AS {n} FROM {n}"
    else:
        sel = f"SELECT resourceinstanceid, obj AS {n} FROM {n}"
    return (
        f"-- ---------------------------------------------------------------------\n"
        f"-- {n}  (cardinality {card(n)})"
        + (f"  children: {', '.join(KIDS[n])}" if KIDS[n] else "")
        + "\n"
        f"-- ---------------------------------------------------------------------\n"
        f"DROP MATERIALIZED VIEW IF EXISTS {S.SCHEMA}.mv_{n} CASCADE;\n"
        f"CREATE MATERIALIZED VIEW {S.SCHEMA}.mv_{n} AS\n"
        f"WITH {body}\n{sel};\n\n"
        f"CREATE UNIQUE INDEX mv_{n}_pk ON {S.SCHEMA}.mv_{n} (resourceinstanceid);\n"
    )


# ---------------- geometry promoted to typed columns ----------------
GEOM_MVS = []


def geom_mv(name, nid, where_ng):
    GEOM_MVS.append(name)
    return (
        f"DROP MATERIALIZED VIEW IF EXISTS {S.SCHEMA}.mv_geom_{name} CASCADE;\n"
        f"CREATE MATERIALIZED VIEW {S.SCHEMA}.mv_geom_{name} AS\n"
        f"SELECT t.resourceinstanceid,\n"
        f"       ST_CollectionHomogenize(ST_Collect(gg.geom)) AS {name}_geom\n"
        f"FROM public.tiles t\n"
        f"JOIN LATERAL (\n"
        f"    SELECT ST_Collect(ST_Transform(g.geom, 4326)) AS geom\n"
        f"    FROM public.geojson_geometries g\n"
        f"    WHERE g.tileid = t.tileid AND g.nodeid = '{nid}'::uuid\n"
        f") gg ON gg.geom IS NOT NULL\n"
        f"WHERE t.nodegroupid = '{where_ng}'::uuid\n"
        f"GROUP BY t.resourceinstanceid;\n\n"
        f"CREATE UNIQUE INDEX mv_geom_{name}_pk ON {S.SCHEMA}.mv_geom_{name} (resourceinstanceid);\n"
        f"CREATE INDEX mv_geom_{name}_gix ON {S.SCHEMA}.mv_geom_{name} USING GIST ({name}_geom);\n"
    )


# ---------------- final matview ----------------
def final_mv():
    cols, joins, jparts = [], [], []
    for i, n in enumerate(TOPS):
        a = f"b{i}"
        if card(n) == "n":
            cols.append(f"    COALESCE({a}.{n}, '[]'::jsonb) AS {n},")
            jparts.append(f"        '{n}', COALESCE({a}.{n}, '[]'::jsonb)")
        else:
            cols.append(f"    {a}.{n},")
            jparts.append(f"        '{n}', {a}.{n}")
        joins.append(
            f"LEFT JOIN {S.SCHEMA}.mv_{n} {a} ON {a}.resourceinstanceid = r.resourceinstanceid"
        )
    for g in GEOM_MVS:
        cols.append(f"    g_{g}.{g}_geom,")
        joins.append(
            f"LEFT JOIN {S.SCHEMA}.mv_geom_{g} g_{g} ON g_{g}.resourceinstanceid = r.resourceinstanceid"
        )
    jb = ",\n".join([f"        'resourceinstanceid', r.resourceinstanceid"] + jparts)
    return (
        f"DROP MATERIALIZED VIEW IF EXISTS {S.SCHEMA}.mv_resource_v1 CASCADE;\n"
        f"CREATE MATERIALIZED VIEW {S.SCHEMA}.mv_resource_v1 AS\n"
        f"SELECT\n    r.resourceinstanceid,\n" + "\n".join(cols) + "\n"
        f"    jsonb_build_object(\n{jb}\n    ) AS resource\n"
        f"FROM public.resource_instances r\n" + "\n".join(joins) + "\n"
        f"WHERE r.graphid = '{S.GRAPH_ID}'::uuid;\n\n"
        f"CREATE UNIQUE INDEX mv_resource_v1_pk ON {S.SCHEMA}.mv_resource_v1 (resourceinstanceid);\n"
        f"CREATE INDEX mv_resource_v1_res ON {S.SCHEMA}.mv_resource_v1 USING GIN (resource jsonb_path_ops);\n"
        + "".join(
            f"CREATE INDEX mv_resource_v1_{g}_gix ON {S.SCHEMA}.mv_resource_v1 USING GIST ({g}_geom);\n"
            for g in GEOM_MVS
        )
    )


# ---------------- emit ----------------
out = []
for n in TOPS:
    out.append(branch_mv(n))
geoms_sql = []
geoms_sql.append(
    geom_mv(
        "site_boundary",
        "b18223c2-13ef-11f0-8695-0242ac170007",
        "b18223c2-13ef-11f0-8695-0242ac170007",
    )
)
geoms_sql.append(
    geom_mv(
        "unprotected_areas",
        "7c8eb1f8-44e2-4239-afaa-9cbf1fadf160",
        "7c8eb1f8-44e2-4239-afaa-9cbf1fadf160",
    )
)

refresh_list = (
    [f"{S.SCHEMA}.mv_geom_{g}" for g in GEOM_MVS]
    + [f"{S.SCHEMA}.mv_{n}" for n in TOPS]
    + [f"{S.SCHEMA}.mv_resource_v1"]
)

open("as_stack_body.sql", "w").write(
    "\n".join(out) + "\n\n"
    "-- =====================================================================\n"
    "-- GEOMETRY promoted to real typed columns. Two geojson nodes in this graph:\n"
    "--   site_boundary      (cardinality 1, on the site_boundary nodegroup)\n"
    "--   unprotected_areas  (cardinality n, on a CHILD of site_boundary)\n"
    "-- Both are also embedded as GeoJSON inside the jsonb object. The typed column\n"
    "-- is what spatial queries need; the GeoJSON is what a web client wants.\n"
    "-- =====================================================================\n"
    + "\n".join(geoms_sql)
    + "\n\n"
    + final_mv()
)

print("top-level branches:", len(TOPS))
for n in TOPS:
    print(f"  {n:38} card={card(n)}  kids={len(KIDS[n])}")
print("nodegroups:", len(S.NG))
print("refresh order:")
for r in refresh_list:
    print("  ", r)
open("as_refresh.txt", "w").write("\n".join(refresh_list))
