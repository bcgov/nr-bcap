#!/usr/bin/env python3
"""Emit the whole MV stack for a graph spec.

    python3 generate.py sv_spec
    python3 generate.py as_spec

Writes <slug>_02_stack.sql, <slug>_03_flat.sql, <slug>_01_preflight.sql.
Everything shared lives in 00_common.sql and is NOT emitted here.
"""

import os
import sys
import importlib
from collections import defaultdict

S = importlib.import_module(sys.argv[1])
out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql", "materialized_views")
)
SC, SLUG = S.SCHEMA, S.SLUG

BY = {n[0]: n for n in S.NG}
KIDS = defaultdict(list)
for n in S.NG:
    if n[2]:
        KIDS[n[2]].append(n[0])
TOPS = [n[0] for n in S.NG if n[2] is None]
GRAINS = list(S.FLAT_GRAINS)

card = lambda n: BY[n][3]
ngid = lambda n: BY[n][1]
fields = lambda n: BY[n][4]
parent = lambda n: BY[n][2]


def chain(n):
    c = []
    while n:
        c.append(n)
        n = parent(n)
    return list(reversed(c))


def geom_field(n):
    for f, nid, dt, _ in fields(n):
        if dt == "geojson-feature-collection":
            return f, nid
    return None


GEOMS = [(n, geom_field(n)[0], geom_field(n)[1]) for n in BY if geom_field(n)]
GEOMS.sort()
GEOM_SUFFIX = ["geom", "geom_type", "source_valid", "points", "lines", "polygons"]


# =====================================================================
# STACK  (nested jsonb object, read straight from public.tiles)
# =====================================================================
def decode(f, nid, dt, fmt, t="t"):
    if dt == "string":
        return f"arches_util.i18n_text({t}.tiledata -> '{nid}')"
    if dt in ("non-localized-string", "borden-number-datatype"):
        return f"{t}.tiledata ->> '{nid}'"  # plain text: the view uses a bare ->>
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


def obj_expr(n, pad):
    p = " " * pad
    parts = []
    for f, nid, dt, fmt in fields(n):
        if dt == "geojson-feature-collection":
            parts.append(
                f"'{f}', CASE WHEN g.geom IS NULL THEN NULL "
                f"ELSE ST_AsGeoJSON(g.geom, 7)::jsonb END"
            )
        else:
            parts.append(f"'{f}', {decode(f, nid, dt, fmt)}")
    for k in KIDS[n]:
        parts.append(
            f"'{k}', COALESCE({k}.arr, '[]'::jsonb)"
            if card(k) == "n"
            else f"'{k}', {k}.obj"
        )
    body = (",\n" + p + "    ").join(parts)
    return f"jsonb_build_object(\n{p}    {body}\n{p})"


def cte(n):
    joins = []
    if geom_field(n):
        joins.append(f"    LEFT JOIN geom_{n} g ON g.tileid = t.tileid")
    for k in KIDS[n]:
        joins.append(f"    LEFT JOIN {k} {k} ON {k}.parenttileid = t.tileid")
    j = ("\n" + "\n".join(joins)) if joins else ""
    top = parent(n) is None
    key = "t.resourceinstanceid" if top else "t.parenttileid"
    kn = "resourceinstanceid" if top else "parenttileid"
    o = obj_expr(n, 8)
    if card(n) == "n":
        return (
            f"{n} AS (\n    SELECT {key} AS {kn},\n"
            f"           jsonb_agg({o} ORDER BY {ORD}) AS arr\n"
            f"    FROM public.tiles t{j}\n"
            f"    WHERE t.nodegroupid = '{ngid(n)}'::uuid\n"
            f"    GROUP BY {key}\n)"
        )
    return (
        f"{n} AS (\n    SELECT DISTINCT ON ({key}) {key} AS {kn},\n"
        f"           {o} AS obj\n"
        f"    FROM public.tiles t{j}\n"
        f"    WHERE t.nodegroupid = '{ngid(n)}'::uuid\n"
        f"    ORDER BY {key}, {ORD}\n)"
    )


def geom_cte(n):
    g = geom_field(n)
    if not g:
        return None
    return (
        f"geom_{n} AS (\n"
        f"    SELECT gg.tileid, ST_Collect(ST_Transform(gg.geom, 4326)) AS geom\n"
        f"    FROM public.geojson_geometries gg\n"
        f"    WHERE gg.nodeid = '{g[1]}'::uuid\n"
        f"    GROUP BY gg.tileid\n)"
    )


def subtree(n):
    out = []
    for k in KIDS[n]:
        out += subtree(k)
    gc = geom_cte(n)
    if gc:
        out.append(gc)
    out.append(cte(n))
    return out


def branch_mv(n):
    sel = (
        f"SELECT resourceinstanceid, arr AS {n} FROM {n}"
        if card(n) == "n"
        else f"SELECT resourceinstanceid, obj AS {n} FROM {n}"
    )
    kids = f"  children: {', '.join(KIDS[n])}" if KIDS[n] else ""
    return (
        f"-- ---------------------------------------------------------------------\n"
        f"-- {n}  (cardinality {card(n)}){kids}\n"
        f"-- ---------------------------------------------------------------------\n"
        f"DROP MATERIALIZED VIEW IF EXISTS {SC}.mv_{n} CASCADE;\n"
        f"CREATE MATERIALIZED VIEW {SC}.mv_{n} AS\nWITH "
        + ",\n".join(subtree(n))
        + f"\n{sel};\n\n"
        f"CREATE UNIQUE INDEX mv_{n}_pk ON {SC}.mv_{n} (resourceinstanceid);\n"
    )


def geom_mv(name, nid, ng):
    return f"""DROP MATERIALIZED VIEW IF EXISTS {SC}.mv_geom_{name} CASCADE;
CREATE MATERIALIZED VIEW {SC}.mv_geom_{name} AS
WITH per_tile AS (
    -- geojson_geometries.geom is SRID 3857 (Web Mercator). The Arches views
    -- ST_Transform on read; so do we. The ::geometry(...,4326) casts ENFORCE it -
    -- drop the transform and the build FAILS rather than publishing Mercator
    -- metres as though they were degrees.
    SELECT t.resourceinstanceid, t.tileid,
           ST_Collect(ST_Transform(g.geom, 4326)) AS geom
    FROM public.tiles t
    JOIN public.geojson_geometries g
      ON g.tileid = t.tileid AND g.nodeid = '{nid}'::uuid
    WHERE t.nodegroupid = '{ng}'::uuid
    GROUP BY t.resourceinstanceid, t.tileid
),
per_res AS (
    SELECT resourceinstanceid, ST_Collect(geom) AS raw
    FROM per_tile GROUP BY resourceinstanceid
),
fixed AS (
    -- ST_Collect over per-tile ST_Collect'd geometries yields a
    -- GEOMETRYCOLLECTION even when every part is a polygon. CollectionHomogenize
    -- collapses that to MULTIPOLYGON / MULTIPOINT / MULTILINESTRING, and leaves a
    -- GEOMETRYCOLLECTION only when the tiles GENUINELY mix types.
    -- MakeValid is applied TWICE on purpose: once on the raw collection, and again
    -- AFTER homogenize, because merging repaired parts into a single MULTIPOLYGON can
    -- itself produce an invalid geometry when tiles overlap. The outer MakeValid is
    -- what guarantees the published column is always valid.
    -- one bad polygon cannot break every downstream spatial query;
    -- {name}_source_valid records which rows needed it. Fix those at source.
    SELECT resourceinstanceid, raw,
           ST_MakeValid(ST_CollectionHomogenize(ST_MakeValid(raw))) AS g
    FROM per_res
)
SELECT resourceinstanceid,
       g::geometry(Geometry, 4326)   AS {name}_geom,
       ST_GeometryType(g)            AS {name}_geom_type,
       ST_IsValid(raw)               AS {name}_source_valid,
       -- CAST OUTSIDE THE CASE. Inside, the NULL branch is coerced to a bare
       -- `geometry` with no typmod, the CASE result drops to typmod -1, and the
       -- column becomes plain `geometry`. PostGIS then registers it in
       -- geometry_columns as srid=0 / type=GEOMETRY and QGIS/GeoServer cannot bind
       -- it. (A toy test with a CONSTANT input hides this - the planner folds the
       -- CASE away and the typmod survives. Against real tables it does not.)
       (CASE WHEN ST_IsEmpty(ST_CollectionExtract(g, 1)) THEN NULL
             ELSE ST_CollectionExtract(g, 1) END)::geometry(MultiPoint, 4326)      AS {name}_points,
       (CASE WHEN ST_IsEmpty(ST_CollectionExtract(g, 2)) THEN NULL
             ELSE ST_CollectionExtract(g, 2) END)::geometry(MultiLineString, 4326) AS {name}_lines,
       (CASE WHEN ST_IsEmpty(ST_CollectionExtract(g, 3)) THEN NULL
             ELSE ST_CollectionExtract(g, 3) END)::geometry(MultiPolygon, 4326)    AS {name}_polygons
FROM fixed;

CREATE UNIQUE INDEX mv_geom_{name}_pk   ON {SC}.mv_geom_{name} (resourceinstanceid);
CREATE INDEX mv_geom_{name}_gix         ON {SC}.mv_geom_{name} USING GIST ({name}_geom);
CREATE INDEX mv_geom_{name}_poly_gix    ON {SC}.mv_geom_{name} USING GIST ({name}_polygons);
CREATE INDEX mv_geom_{name}_pt_gix      ON {SC}.mv_geom_{name} USING GIST ({name}_points);
CREATE INDEX mv_geom_{name}_line_gix    ON {SC}.mv_geom_{name} USING GIST ({name}_lines);
"""


def final_mv():
    cols, joins, jb = [], [], []
    for i, n in enumerate(TOPS):
        a = f"b{i}"
        if card(n) == "n":
            cols.append(f"    COALESCE({a}.{n}, '[]'::jsonb) AS {n},")
            jb.append(f"        '{n}', COALESCE({a}.{n}, '[]'::jsonb)")
        else:
            cols.append(f"    {a}.{n},")
            jb.append(f"        '{n}', {a}.{n}")
        joins.append(
            f"LEFT JOIN {SC}.mv_{n} {a} ON {a}.resourceinstanceid = r.resourceinstanceid"
        )
    for ng, fname, nid in GEOMS:
        for s in GEOM_SUFFIX:
            cols.append(f"    g_{fname}.{fname}_{s},")
        joins.append(
            f"LEFT JOIN {SC}.mv_geom_{fname} g_{fname} ON g_{fname}.resourceinstanceid = r.resourceinstanceid"
        )
    body = ",\n".join([f"        'resourceinstanceid', r.resourceinstanceid"] + jb)
    idx = "".join(
        f"CREATE INDEX mv_resource_v1_{f}_gix      ON {SC}.mv_resource_v1 USING GIST ({f}_geom);\n"
        f"CREATE INDEX mv_resource_v1_{f}_poly_gix ON {SC}.mv_resource_v1 USING GIST ({f}_polygons);\n"
        for _, f, _ in GEOMS
    )
    return (
        f"DROP MATERIALIZED VIEW IF EXISTS {SC}.mv_resource_v1 CASCADE;\n"
        f"CREATE MATERIALIZED VIEW {SC}.mv_resource_v1 AS\n"
        f"-- resource_instances is the row DRIVER, not a source of columns. It is what\n"
        f"-- guarantees one row per resource INCLUDING resources with zero tiles, and it\n"
        f"-- carries the only graphid filter in the stack. Drop the columns, keep the join.\n"
        f"SELECT\n    r.resourceinstanceid,\n" + "\n".join(cols) + "\n"
        f"    jsonb_build_object(\n{body}\n    ) AS resource\n"
        f"FROM public.resource_instances r\n" + "\n".join(joins) + "\n"
        f"WHERE r.graphid = '{S.GRAPH_ID}'::uuid;\n\n"
        f"CREATE UNIQUE INDEX mv_resource_v1_pk  ON {SC}.mv_resource_v1 (resourceinstanceid);\n"
        f"CREATE INDEX mv_resource_v1_res        ON {SC}.mv_resource_v1 USING GIN (resource jsonb_path_ops);\n"
        + idx
    )


REFRESH = (
    [f"{SC}.mv_geom_{f}" for _, f, _ in GEOMS]
    + [f"{SC}.mv_{n}" for n in TOPS]
    + [f"{SC}.mv_resource_v1"]
)

SC_DIR = os.path.join(out_dir, SC)
os.makedirs(SC_DIR, exist_ok=True)

_HEAD = (
    f"-- GENERATED - edit {sys.argv[1]}.py and re-run generate.py. Do not hand-edit.\n"
    f"-- Graph {S.GRAPH_ID}\n"
    f"-- Requires 00_arches_util.sql (arches_util helpers) to be applied first.\n"
    f"--\n"
    f"-- Reads public.tiles DIRECTLY. The generated {SC}.* views are NOT used:\n"
    f"-- each LEFT JOINs edit_log twice with a text->uuid cast that no index can serve.\n"
    f"--\n"
    f"-- INVARIANTS (downstream depends on these - do not change silently):\n"
    f"--   * every key ALWAYS present; empty means null, never absent. No jsonb_strip_nulls.\n"
    f"--   * cardinality-n children are ALWAYS a jsonb array, [] when empty, never null.\n"
    f"--   * cardinality-1 branches are an object, or null when the tile does not exist.\n"
    f"--   * array order is tiles.sortorder, then tileid. Stable across refreshes.\n\n"
    f"SET client_min_messages = warning;   -- ST_MakeValid emits a NOTICE per repair\n"
    f"SET maintenance_work_mem = '512MB';\n"
    f"SET work_mem             = '128MB';\n\n"
    f"CREATE SCHEMA IF NOT EXISTS {SC};\n\n"
)

for n in TOPS:
    open(os.path.join(SC_DIR, f"mv_{n}.sql"), "w").write(_HEAD + branch_mv(n))

for ng, fname, nid in GEOMS:
    open(os.path.join(SC_DIR, f"mv_geom_{fname}.sql"), "w").write(_HEAD + geom_mv(fname, nid, ngid(ng)))

open(os.path.join(SC_DIR, "mv_resource_v1.sql"), "w").write(_HEAD + final_mv())

open(os.path.join(SC_DIR, "resource_view.sql"), "w").write(
    "-- GENERATED - edit " + sys.argv[1] + ".py and re-run generate.py. Do not hand-edit.\n"
    "-- Wrapper view — the downstream contract. Repoint the backing matview here,\n"
    "-- never rename this view. To ship v2: build mv_resource_v2, verify, repoint.\n\n"
    f"CREATE OR REPLACE VIEW {SC}.resource AS SELECT * FROM {SC}.mv_resource_v1;\n\n"
    f"COMMENT ON VIEW {SC}.resource IS\n"
    f"'Stable read contract for the {SC} graph. One row per resource instance. Backed by a '\n"
    f"'materialized view - repoint the backing matview here, never rename this. Arrays are always '\n"
    f"'[] when empty, never null. Cardinality-1 branches are null when the tile does not exist.';\n\n"
    f"-- GRANT SELECT ON {SC}.resource TO <app_role>;   -- never grant on mv_resource_v1\n"
)

open(os.path.join(SC_DIR, "refresh_resource.sql"), "w").write(
    "-- GENERATED - edit " + sys.argv[1] + ".py and re-run generate.py. Do not hand-edit.\n"
    "-- Refresh order: geometry first (branches embed GeoJSON), then branches, then final.\n\n"
    f"CREATE OR REPLACE PROCEDURE {SC}.refresh_resource(concurrent boolean DEFAULT true)\n"
    f"LANGUAGE plpgsql AS $$\n"
    f"DECLARE\n"
    f"    mode text := CASE WHEN concurrent THEN 'CONCURRENTLY' ELSE '' END;\n"
    f"    mv   text;\n"
    f"BEGIN\n"
    f"    FOREACH mv IN ARRAY ARRAY[\n"
    + ",\n".join(f"        '{m}'" for m in REFRESH)
    + "\n"
    "    ]\n"
    "    LOOP\n"
    "        RAISE NOTICE 'refreshing %', mv;\n"
    "        EXECUTE format('REFRESH MATERIALIZED VIEW %s %s', mode, mv);\n"
    "        COMMIT;\n"
    "    END LOOP;\n"
    "END $$;\n"
)


# =====================================================================
# FLAT
# =====================================================================
D, ID = "' | '", "'; '"


def n_depth(n, root=None):
    """count cardinality-n nodegroups between root (exclusive) and n (inclusive)"""
    c = chain(n)
    if root:
        c = c[c.index(root) + 1 :]
    return sum(1 for x in c if card(x) == "n")


def grain_of(n):
    """innermost FLAT_GRAIN that is an ancestor-or-self of n; None -> resource_flat"""
    for x in reversed(chain(n)):
        if x in GRAINS:
            return x
    return None


def obj_path(n, root):
    """object path from a root's tile element down to n's container"""
    c = chain(n)
    return c[c.index(root) + 1 :] if root else c


def plit(p):
    return "'{" + ",".join(p) + "}'::text[]" if p else "'{}'::text[]"


def emit_scalar(cols, ng, base):
    for f, nid, dt, fmt in fields(ng):
        if dt == "geojson-feature-collection":
            continue
        v = f"{base} -> '{f}'"
        if dt in ("string", "non-localized-string", "borden-number-datatype"):
            cols.append((f, f"{base} ->> '{f}'"))
        elif dt == "number":
            cols.append((f, f"({base} ->> '{f}')::numeric"))
        elif dt == "boolean":
            cols.append((f, f"({base} ->> '{f}')::boolean"))
        elif dt == "date":
            cols.append((f, f"({base} ->> '{f}')::date"))
        elif dt == "reference":
            cols.append((f, f"arches_util.a2csv({v}, 'label', {D})"))
            cols.append((f + "_ids", f"arches_util.a2csv({v}, 'list_item_id', {D})"))
        elif dt == "resource-instance":
            cols.append(
                (f, f"arches_util.resource_name(arches_util.to_uuid({base} ->> '{f}'))")
            )
            cols.append((f + "_id", f"{base} ->> '{f}'"))
        elif dt == "resource-instance-list":
            cols.append((f, f"arches_util.resource_names_csv({v}, {D})"))
            cols.append((f + "_ids", f"arches_util.a2csv({v}, NULL, {D})"))
        elif dt == "file-list":
            cols.append((f, f"arches_util.a2csv({v}, 'name', {D})"))
            cols.append((f + "_file_ids", f"arches_util.a2csv({v}, 'file_id', {D})"))
        elif dt == "url":
            cols.append((f, f"{v} ->> 'url'"))
            cols.append((f + "_label", f"{v} ->> 'label'"))


def emit_csv(cols, ng, arr, path):
    P = plit(path)
    for f, nid, dt, fmt in fields(ng):
        if dt == "geojson-feature-collection":
            continue
        if dt in (
            "string",
            "non-localized-string",
            "borden-number-datatype",
            "number",
            "boolean",
            "date",
        ):
            cols.append((f, f"arches_util.deep_csv({arr}, {P}, '{f}', {D})"))
        elif dt == "reference":
            cols.append(
                (
                    f,
                    f"arches_util.deep_csv_nested({arr}, {P}, '{f}', 'label', {D}, {ID})",
                )
            )
            cols.append(
                (
                    f + "_ids",
                    f"arches_util.deep_csv_nested({arr}, {P}, '{f}', 'list_item_id', {D}, {ID})",
                )
            )
        elif dt == "resource-instance":
            cols.append((f, f"arches_util.deep_res_csv({arr}, {P}, '{f}', {D})"))
            cols.append((f + "_ids", f"arches_util.deep_csv({arr}, {P}, '{f}', {D})"))
        elif dt == "resource-instance-list":
            cols.append(
                (f, f"arches_util.deep_res_csv_nested({arr}, {P}, '{f}', {D}, {ID})")
            )
            cols.append(
                (
                    f + "_ids",
                    f"arches_util.deep_csv_nested({arr}, {P}, '{f}', NULL, {D}, {ID})",
                )
            )
        elif dt == "file-list":
            cols.append(
                (
                    f,
                    f"arches_util.deep_csv_nested({arr}, {P}, '{f}', 'name', {D}, {ID})",
                )
            )
            cols.append(
                (
                    f + "_file_ids",
                    f"arches_util.deep_csv_nested({arr}, {P}, '{f}', 'file_id', {D}, {ID})",
                )
            )
        elif dt == "url":
            # percent-encode '|' rather than substituting '/': substituting would
            # silently CORRUPT a url containing a pipe. %7C still resolves.
            cols.append((f, f"arches_util.deep_url_csv({arr}, {P}, '{f}', {D})"))
            cols.append(
                (
                    f + "_label",
                    f"arches_util.deep_csv_sub({arr}, {P}, '{f}', 'label', {D})",
                )
            )


def build_table(root):
    """root=None -> resource_flat (grain: resource). else grain: one row per root tile."""
    cols = []
    members = [n for n in BY if grain_of(n) == root]
    for n in sorted(members, key=lambda x: len(chain(x))):
        # where does this nodegroup's data hang, relative to the grain?
        if root is None:
            top = chain(n)[0]
            base = f"r.{top}"
            rel = n_depth(n)
            path = obj_path(n, top)[:-1] if card(top) == "n" else obj_path(n, None)[1:]
        else:
            base = "g.t"
            rel = n_depth(n, root)
            path = obj_path(n, root)
        if rel == 0:
            if root is None:
                expr = base + "".join(f" -> '{x}'" for x in obj_path(n, None)[1:])
            else:
                expr = base + "".join(f" -> '{x}'" for x in path)
            emit_scalar(cols, n, expr)
        elif rel == 1:
            # the single cardinality-n nodegroup on the way down
            c = chain(n) if root is None else chain(n)[chain(n).index(root) + 1 :]
            arr_ng = next(x for x in c if card(x) == "n")
            if root is None:
                pre = chain(arr_ng)
                arr = (
                    "r." + pre[0]
                    if len(pre) == 1
                    else "r." + pre[0] + "".join(f" -> '{x}'" for x in pre[1:])
                )
            else:
                pre = obj_path(arr_ng, root)
                arr = base + "".join(f" -> '{x}'" for x in pre)
            after = chain(n)[chain(n).index(arr_ng) + 1 :]
            emit_csv(cols, n, arr, after)
            cnt = (n, arr)
            if not any(c0 == f"{arr_ng}_count" for c0, _ in cols):
                cols.append(
                    (
                        f"{arr_ng}_count",
                        f"jsonb_array_length(arches_util.as_array({arr}))",
                    )
                )
    # pointers to child grain tables
    for gname in GRAINS:
        if grain_of(parent(gname)) == root or (root is None and parent(gname) is None):
            pass
    return cols


def grain_arr_expr(gname):
    c = chain(gname)
    if len(c) == 1:
        return f"r.{c[0]}"
    return f"r.{c[0]}" + "".join(f" -> '{x}'" for x in c[1:])


# resource_flat
res_cols = build_table(None)
# grain tables
grain_tables = []
for gname in GRAINS:
    gcols = build_table(gname)
    grain_tables.append((gname, gcols))


def render(name, cols, frm, extra_pk):
    sel = ",\n".join(f"    {e} AS {c}" for c, e in cols)
    idx = f"CREATE UNIQUE INDEX mv_{name}_pk ON {SC}.mv_{name} ({extra_pk});\n"
    return (
        f"DROP MATERIALIZED VIEW IF EXISTS {SC}.mv_{name} CASCADE;\n"
        f"CREATE MATERIALIZED VIEW {SC}.mv_{name} AS\n{frm.format(sel=sel)}\n\n{idx}"
    )


geom_cols = "".join(
    f"    r.{f}_geom,\n    r.{f}_geom_type,\n    r.{f}_source_valid,\n"
    f"    r.{f}_points,\n    r.{f}_lines,\n    r.{f}_polygons,\n"
    for _, f, _ in GEOMS
)

_FLAT_HEAD = (
    "-- GENERATED - edit " + sys.argv[1] + ".py and re-run generate.py.\n"
    f"-- Requires {SC}/mv_resource_v1.sql to be applied first.\n"
    f"--\n"
    f"-- Built ON TOP OF mv_resource_v1: one source of truth, zero joins.\n"
    f"-- CONTRACT:\n"
    f"--   * cardinality-1 fields keep REAL TYPES (date, numeric, boolean, text)\n"
    f"--   * cardinality-n fields are TEXT CSV: ' | ' between tiles, '; ' within a tile\n"
    f"--   * POSITIONAL ALIGNMENT IS THE CONTRACT. Null elements emit an EMPTY SLOT.\n"
    f"--   * references come in pairs: x (labels) + x_ids\n\n"
    f"SET client_min_messages = warning;\n\n"
)

_body = render(
    "resource_flat_v1",
    res_cols,
    "SELECT\n    r.resourceinstanceid,\n" + geom_cols + "{sel}\n"
    f"FROM {SC}.mv_resource_v1 r;",
    "resourceinstanceid",
)
for _, f, _ in GEOMS:
    _body += f"CREATE INDEX mv_resource_flat_v1_{f}_gix ON {SC}.mv_resource_flat_v1 USING GIST ({f}_geom);\n"
open(os.path.join(SC_DIR, "mv_resource_flat_v1.sql"), "w").write(_FLAT_HEAD + _body)

for gname, gcols in grain_tables:
    par = parent(gname)
    pg = grain_of(par) if par else None
    if pg is None:
        frm = (
            "SELECT\n    r.resourceinstanceid,\n    g.ord AS {gname}_index,\n{sel}\n"
            f"FROM {SC}.mv_resource_v1 r,\n"
            f"     LATERAL jsonb_array_elements(arches_util.as_array({grain_arr_expr(gname)}))\n"
            f"             WITH ORDINALITY AS g(t, ord);"
        ).replace("{gname}", gname)
        pk = f"resourceinstanceid, {gname}_index"
    else:
        pre = obj_path(gname, pg)
        inner = "p.t" + "".join(f" -> '{x}'" for x in pre)
        frm = (
            "SELECT\n    r.resourceinstanceid,\n"
            f"    p.ord AS {pg}_index,\n    g.ord AS {gname}_index,\n" + "{sel}\n"
            f"FROM {SC}.mv_resource_v1 r,\n"
            f"     LATERAL jsonb_array_elements(arches_util.as_array({grain_arr_expr(pg)}))\n"
            f"             WITH ORDINALITY AS p(t, ord),\n"
            f"     LATERAL jsonb_array_elements(arches_util.as_array({inner}))\n"
            f"             WITH ORDINALITY AS g(t, ord);"
        )
        pk = f"resourceinstanceid, {pg}_index, {gname}_index"
    open(os.path.join(SC_DIR, f"mv_{gname}_flat_v1.sql"), "w").write(
        _FLAT_HEAD + render(f"{gname}_flat_v1", gcols, frm, pk)
    )

wraps = [("resource_flat", "resource_flat_v1")] + [
    (f"{g}_flat", f"{g}_flat_v1") for g in GRAINS
]
_fv = "-- GENERATED - edit " + sys.argv[1] + ".py and re-run generate.py. Do not hand-edit.\n\n"
for w, m in wraps:
    _fv += f"CREATE OR REPLACE VIEW {SC}.{w} AS SELECT * FROM {SC}.mv_{m};\n"
_fv += (
    f"\nCOMMENT ON VIEW {SC}.resource_flat IS\n"
    f"'Flat {SC} records, one row per resource. Cardinality-n values are delimiter-joined text '\n"
    f"'(\" | \" between tiles, \"; \" within a tile) and are POSITIONALLY ALIGNED with their siblings - '\n"
    f"'empty slots are meaningful, do not strip them. Deeply nested subtrees live in the *_flat '\n"
    f"'companion tables, joined on resourceinstanceid.';\n"
)
open(os.path.join(SC_DIR, "flat_views.sql"), "w").write(_fv)

open(os.path.join(SC_DIR, "refresh_flat.sql"), "w").write(
    "-- GENERATED - edit " + sys.argv[1] + ".py and re-run generate.py. Do not hand-edit.\n\n"
    f"CREATE OR REPLACE PROCEDURE {SC}.refresh_flat(concurrent boolean DEFAULT true)\n"
    f"LANGUAGE plpgsql AS $$\n"
    f"DECLARE\n"
    f"    mode text := CASE WHEN concurrent THEN 'CONCURRENTLY' ELSE '' END;\n"
    f"    mv   text;\n"
    f"BEGIN\n"
    f"    FOREACH mv IN ARRAY ARRAY[\n"
    + ",\n".join(f"        '{SC}.mv_{m}'" for _, m in wraps)
    + "\n"
    "    ]\n"
    "    LOOP\n"
    "        RAISE NOTICE 'refreshing %', mv;\n"
    "        EXECUTE format('REFRESH MATERIALIZED VIEW %s %s', mode, mv);\n"
    "        COMMIT;\n"
    "    END LOOP;\n"
    "END $$;\n"
)

# alignment regression test — run manually after build, not tracked by django_migrate_sql
tabs = [("resource_flat_v1", res_cols)] + [(f"{g}_flat_v1", c) for g, c in grain_tables]
parts = []
for tname, cols in tabs:
    groups = defaultdict(list)
    counts = {}
    import re as _re

    for c, e in cols:
        m = _re.match(
            r"arches_util\.(deep_csv\w*|deep_res_csv\w*|deep_url_csv)\((.+?),\s*('\{[^}]*\}'::text\[\])",
            e,
        )
        if m:
            groups[(m.group(2).strip(), m.group(3))].append(c)
        m2 = _re.match(r"jsonb_array_length\(arches_util\.as_array\((.+?)\)\)$", e)
        if m2:
            counts[m2.group(1).strip()] = c
    for (arr, path), cs in groups.items():
        if arr not in counts:
            continue
        cnt = counts[arr]
        parts.append(
            f"  SELECT resourceinstanceid, {cnt} AS n, '{tname}.{cnt[:-6]}' AS grp,\n"
            f"         ARRAY["
            + ",\n               ".join(f"arches_util.nslots({c})" for c in cs)
            + "] AS slots,\n"
            f"         ARRAY["
            + ", ".join(f"'{c}'" for c in cs)
            + "]::text[] AS colnames\n"
            f"  FROM {SC}.mv_{tname} WHERE {cnt} > 0"
        )

open(os.path.join(SC_DIR, "alignment_test.sql"), "w").write(
    "-- Alignment regression test. Run after every build. EXPECT ZERO ROWS.\n"
    "-- Not a schema object - run manually to verify correctness.\n"
    "--\n"
    "-- Every sibling column from one cardinality-n nodegroup must have exactly\n"
    "-- <nodegroup>_count slots. A mismatch means a null element got SKIPPED.\n"
    "-- =====================================================================\n"
    "WITH v AS (\n"
    + "\n  UNION ALL\n".join(parts)
    + "\n)\n"
    "SELECT grp, colname,\n"
    "       count(DISTINCT resourceinstanceid) AS rows_affected,\n"
    "       count(*)                           AS bad_cells\n"
    "FROM v, LATERAL unnest(slots, colnames) AS u(sl, colname)\n"
    "WHERE sl IS DISTINCT FROM n\n"
    "GROUP BY grp, colname\n"
    "ORDER BY rows_affected DESC, grp, colname;\n"
)

names = [c for c, _ in res_cols]
dupes = sorted({c for c in names if names.count(c) > 1})
assert not dupes, f"duplicate columns in resource_flat: {dupes}"
print(
    f"{SLUG}: {len(TOPS)} branches, {len(S.NG)} nodegroups, {len(GEOMS)} geometry nodes"
)
print(f"   resource_flat : {len(res_cols)+1+6*len(GEOMS)} cols")
for g, c in grain_tables:
    print(f"   {g}_flat : {len(c)} cols")
print(f"   alignment groups: {len(parts)}")
