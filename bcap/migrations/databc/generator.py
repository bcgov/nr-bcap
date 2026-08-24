"""
Materialized view SQL generator for DataBC resource models.

Import and use directly:
    from bcap.migrations.databc.generator import SpecGenerator
    gen = SpecGenerator(spec, out_dir)
    results = gen.generate()
    flat_cols = gen.get_flat_columns()          # resource_flat columns
    grain_cols = gen.get_flat_columns("grain")  # grain flat columns

spec must have:
    GRAPH_ID, SCHEMA, SLUG, FLAT_GRAINS  (list of nodegroup aliases)
    NG         list of (alias, ngid, parent_alias_or_None, cardinality, fields)
    fields     list of (field_alias, nodeid, datatype, datefmt_or_None)
    FLAT_GRAIN_VIEW_NAMES (optional) dict mapping alias -> stable wrapper view name
"""

import os
import re
from collections import defaultdict


class SpecGenerator:
    """Generates the full MV + flat SQL stack from a graph spec object."""

    _ORD = "COALESCE(t.sortorder, 2147483647), t.tileid"
    _GEOM_SUFFIX = ["geom", "geom_type", "source_valid", "points", "lines", "polygons"]
    _D = "' | '"  # tile delimiter
    _ID = "'; '"  # inner delimiter

    def __init__(self, spec, out_dir):
        self.GRAPH_ID = spec.GRAPH_ID
        self.SC = spec.SCHEMA
        self.SLUG = spec.SLUG
        self.GRAINS = list(spec.FLAT_GRAINS)
        self.GRAIN_VIEW_NAMES = getattr(spec, "FLAT_GRAIN_VIEW_NAMES", {})
        self.schema_dir = os.path.join(out_dir, self.SC)

        self.BY = {n[0]: n for n in spec.NG}
        self.KIDS = defaultdict(list)
        for n in spec.NG:
            if n[2]:
                self.KIDS[n[2]].append(n[0])
        self.TOPS = [n[0] for n in spec.NG if n[2] is None]
        self.GEOMS = sorted(
            [
                (n, self._geom_field(n)[0], self._geom_field(n)[1])
                for n in self.BY
                if self._geom_field(n)
            ]
        )

    # -----------------------------------------------------------------------
    # Accessors
    # -----------------------------------------------------------------------
    def _card(self, n):
        return self.BY[n][3]

    def _ngid(self, n):
        return self.BY[n][1]

    def _fields(self, n):
        return self.BY[n][4]

    def _parent(self, n):
        return self.BY[n][2]

    def _chain(self, n):
        c = []
        while n:
            c.append(n)
            n = self._parent(n)
        return list(reversed(c))

    def _geom_field(self, n):
        for f, nid, dt, _ in self.BY.get(n, ("", "", "", "", []))[4]:
            if dt == "geojson-feature-collection":
                return f, nid
        return None

    def _grain_of(self, n):
        """Innermost FLAT_GRAIN that is an ancestor-or-self of n; None → resource_flat."""
        for x in reversed(self._chain(n)):
            if x in self.GRAINS:
                return x
        return None

    def _obj_path(self, n, root):
        """Chain from after root down to n (inclusive)."""
        c = self._chain(n)
        return c[c.index(root) + 1 :] if root else c

    def _n_depth(self, n, root=None):
        """Count cardinality-n nodegroups between root (exclusive) and n (inclusive)."""
        c = self._chain(n)
        if root:
            c = c[c.index(root) + 1 :]
        return sum(1 for x in c if self._card(x) == "n")

    def _grain_view_name(self, grain):
        """Stable wrapper view name for a grain (may differ from the nodegroup alias)."""
        return self.GRAIN_VIEW_NAMES.get(grain, grain)

    # -----------------------------------------------------------------------
    # Stack SQL
    # -----------------------------------------------------------------------
    def _decode(self, f, nid, dt, fmt, t="t"):
        if dt == "string":
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
        raise ValueError(f"Unknown datatype: {dt}")

    def _obj_expr(self, n, pad):
        p = " " * pad
        parts = []
        for f, nid, dt, fmt in self._fields(n):
            if dt == "geojson-feature-collection":
                parts.append(
                    f"'{f}', CASE WHEN g.geom IS NULL THEN NULL "
                    f"ELSE ST_AsGeoJSON(g.geom, 7)::jsonb END"
                )
            else:
                parts.append(f"'{f}', {self._decode(f, nid, dt, fmt)}")
        for k in self.KIDS[n]:
            parts.append(
                f"'{k}', COALESCE({k}.arr, '[]'::jsonb)"
                if self._card(k) == "n"
                else f"'{k}', {k}.obj"
            )
        body = (",\n" + p + "    ").join(parts)
        return f"jsonb_build_object(\n{p}    {body}\n{p})"

    def _cte(self, n):
        joins = []
        if self._geom_field(n):
            joins.append(f"    LEFT JOIN geom_{n} g ON g.tileid = t.tileid")
        for k in self.KIDS[n]:
            joins.append(f"    LEFT JOIN {k} {k} ON {k}.parenttileid = t.tileid")
        j = ("\n" + "\n".join(joins)) if joins else ""
        top = self._parent(n) is None
        key = "t.resourceinstanceid" if top else "t.parenttileid"
        kn = "resourceinstanceid" if top else "parenttileid"
        o = self._obj_expr(n, 8)
        if self._card(n) == "n":
            return (
                f"{n} AS (\n    SELECT {key} AS {kn},\n"
                f"           jsonb_agg({o} ORDER BY {self._ORD}) AS arr\n"
                f"    FROM public.tiles t{j}\n"
                f"    WHERE t.nodegroupid = '{self._ngid(n)}'::uuid\n"
                f"    GROUP BY {key}\n)"
            )
        return (
            f"{n} AS (\n    SELECT DISTINCT ON ({key}) {key} AS {kn},\n"
            f"           {o} AS obj\n"
            f"    FROM public.tiles t{j}\n"
            f"    WHERE t.nodegroupid = '{self._ngid(n)}'::uuid\n"
            f"    ORDER BY {key}, {self._ORD}\n)"
        )

    def _geom_cte(self, n):
        g = self._geom_field(n)
        if not g:
            return None
        return (
            f"geom_{n} AS (\n"
            f"    SELECT gg.tileid, ST_Collect(ST_Transform(gg.geom, 4326)) AS geom\n"
            f"    FROM public.geojson_geometries gg\n"
            f"    WHERE gg.nodeid = '{g[1]}'::uuid\n"
            f"    GROUP BY gg.tileid\n)"
        )

    def _subtree(self, n):
        out = []
        for k in self.KIDS[n]:
            out += self._subtree(k)
        gc = self._geom_cte(n)
        if gc:
            out.append(gc)
        out.append(self._cte(n))
        return out

    def _branch_mv_sql(self, n):
        kids = f"  children: {', '.join(self.KIDS[n])}" if self.KIDS[n] else ""
        sel = (
            f"SELECT resourceinstanceid, arr AS {n} FROM {n}"
            if self._card(n) == "n"
            else f"SELECT resourceinstanceid, obj AS {n} FROM {n}"
        )
        return (
            f"-- ---------------------------------------------------------------------\n"
            f"-- {n}  (cardinality {self._card(n)}){kids}\n"
            f"-- ---------------------------------------------------------------------\n"
            f"DROP MATERIALIZED VIEW IF EXISTS {self.SC}.mv_{n} CASCADE;\n"
            f"CREATE MATERIALIZED VIEW {self.SC}.mv_{n} AS\nWITH "
            + ",\n".join(self._subtree(n))
            + f"\n{sel};\n\n"
            f"CREATE UNIQUE INDEX mv_{n}_pk ON {self.SC}.mv_{n} (resourceinstanceid);\n"
        )

    def _geom_mv_sql(self, fname, nid, ng_id):
        return (
            f"DROP MATERIALIZED VIEW IF EXISTS {self.SC}.mv_geom_{fname} CASCADE;\n"
            f"CREATE MATERIALIZED VIEW {self.SC}.mv_geom_{fname} AS\n"
            f"WITH per_tile AS (\n"
            f"    SELECT t.resourceinstanceid, t.tileid,\n"
            f"           ST_Collect(ST_Transform(g.geom, 4326)) AS geom\n"
            f"    FROM public.tiles t\n"
            f"    JOIN public.geojson_geometries g\n"
            f"      ON g.tileid = t.tileid AND g.nodeid = '{nid}'::uuid\n"
            f"    WHERE t.nodegroupid = '{ng_id}'::uuid\n"
            f"    GROUP BY t.resourceinstanceid, t.tileid\n"
            f"),\n"
            f"per_res AS (\n"
            f"    SELECT resourceinstanceid, ST_Collect(geom) AS raw\n"
            f"    FROM per_tile GROUP BY resourceinstanceid\n"
            f"),\n"
            f"fixed AS (\n"
            f"    SELECT resourceinstanceid, raw,\n"
            f"           ST_MakeValid(ST_CollectionHomogenize(ST_MakeValid(raw))) AS g\n"
            f"    FROM per_res\n"
            f")\n"
            f"SELECT resourceinstanceid,\n"
            f"       g::geometry(Geometry, 4326)   AS {fname}_geom,\n"
            f"       ST_GeometryType(g)            AS {fname}_geom_type,\n"
            f"       ST_IsValid(raw)               AS {fname}_source_valid,\n"
            f"       (CASE WHEN ST_IsEmpty(ST_CollectionExtract(g, 1)) THEN NULL\n"
            f"             ELSE ST_CollectionExtract(g, 1) END)::geometry(MultiPoint, 4326)      AS {fname}_points,\n"
            f"       (CASE WHEN ST_IsEmpty(ST_CollectionExtract(g, 2)) THEN NULL\n"
            f"             ELSE ST_CollectionExtract(g, 2) END)::geometry(MultiLineString, 4326) AS {fname}_lines,\n"
            f"       (CASE WHEN ST_IsEmpty(ST_CollectionExtract(g, 3)) THEN NULL\n"
            f"             ELSE ST_CollectionExtract(g, 3) END)::geometry(MultiPolygon, 4326)    AS {fname}_polygons\n"
            f"FROM fixed;\n\n"
            f"CREATE UNIQUE INDEX mv_geom_{fname}_pk   ON {self.SC}.mv_geom_{fname} (resourceinstanceid);\n"
            f"CREATE INDEX mv_geom_{fname}_gix         ON {self.SC}.mv_geom_{fname} USING GIST ({fname}_geom);\n"
            f"CREATE INDEX mv_geom_{fname}_poly_gix    ON {self.SC}.mv_geom_{fname} USING GIST ({fname}_polygons);\n"
            f"CREATE INDEX mv_geom_{fname}_pt_gix      ON {self.SC}.mv_geom_{fname} USING GIST ({fname}_points);\n"
            f"CREATE INDEX mv_geom_{fname}_line_gix    ON {self.SC}.mv_geom_{fname} USING GIST ({fname}_lines);\n"
        )

    def _final_mv_sql(self):
        cols, joins, jb = [], [], []
        for i, n in enumerate(self.TOPS):
            a = f"b{i}"
            if self._card(n) == "n":
                cols.append(f"    COALESCE({a}.{n}, '[]'::jsonb) AS {n},")
                jb.append(f"        '{n}', COALESCE({a}.{n}, '[]'::jsonb)")
            else:
                cols.append(f"    {a}.{n},")
                jb.append(f"        '{n}', {a}.{n}")
            joins.append(
                f"LEFT JOIN {self.SC}.mv_{n} {a} ON {a}.resourceinstanceid = r.resourceinstanceid"
            )
        for _ng, fname, _nid in self.GEOMS:
            for s in self._GEOM_SUFFIX:
                cols.append(f"    g_{fname}.{fname}_{s},")
            joins.append(
                f"LEFT JOIN {self.SC}.mv_geom_{fname} g_{fname}"
                f" ON g_{fname}.resourceinstanceid = r.resourceinstanceid"
            )
        body = ",\n".join([f"        'resourceinstanceid', r.resourceinstanceid"] + jb)
        geom_idx = "".join(
            f"CREATE INDEX mv_resource_{f}_gix      ON {self.SC}.mv_resource USING GIST ({f}_geom);\n"
            f"CREATE INDEX mv_resource_{f}_poly_gix ON {self.SC}.mv_resource USING GIST ({f}_polygons);\n"
            for _, f, _ in self.GEOMS
        )
        return (
            f"DROP MATERIALIZED VIEW IF EXISTS {self.SC}.mv_resource CASCADE;\n"
            f"CREATE MATERIALIZED VIEW {self.SC}.mv_resource AS\n"
            f"-- resource_instances is the row driver: one row per resource including\n"
            f"-- resources with zero tiles; carries the graphid filter.\n"
            f"SELECT\n"
            f"    r.resourceinstanceid,\n" + "\n".join(cols) + "\n"
            f"    jsonb_build_object(\n{body}\n    ) AS resource\n"
            f"FROM public.resource_instances r\n" + "\n".join(joins) + "\n"
            f"WHERE r.graphid = '{self.GRAPH_ID}'::uuid;\n\n"
            f"CREATE UNIQUE INDEX mv_resource_pk  ON {self.SC}.mv_resource (resourceinstanceid);\n"
            f"CREATE INDEX mv_resource_res        ON {self.SC}.mv_resource USING GIN (resource jsonb_path_ops);\n"
            + geom_idx
        )

    # -----------------------------------------------------------------------
    # Flat SQL
    # -----------------------------------------------------------------------
    def _plit(self, p):
        return "'{" + ",".join(p) + "}'::text[]" if p else "'{}'::text[]"

    def _emit_scalar(self, cols, ng, base):
        for f, nid, dt, _fmt in self._fields(ng):
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
                cols.append((f, f"arches_util.a2csv({v}, 'label', {self._D})"))
                cols.append(
                    (f"{f}_ids", f"arches_util.a2csv({v}, 'list_item_id', {self._D})")
                )
            elif dt == "resource-instance":
                cols.append(
                    (
                        f,
                        f"arches_util.resource_name(arches_util.to_uuid({base} ->> '{f}'))",
                    )
                )
                cols.append((f"{f}_id", f"{base} ->> '{f}'"))
            elif dt == "resource-instance-list":
                cols.append((f, f"arches_util.resource_names_csv({v}, {self._D})"))
                cols.append((f"{f}_ids", f"arches_util.a2csv({v}, NULL, {self._D})"))
            elif dt == "file-list":
                cols.append((f, f"arches_util.a2csv({v}, 'name', {self._D})"))
                cols.append(
                    (f"{f}_file_ids", f"arches_util.a2csv({v}, 'file_id', {self._D})")
                )
            elif dt == "url":
                cols.append((f, f"{v} ->> 'url'"))
                cols.append((f"{f}_label", f"{v} ->> 'label'"))

    def _emit_csv(self, cols, ng, arr, path):
        P = self._plit(path)
        for f, _nid, dt, _fmt in self._fields(ng):
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
                cols.append((f, f"arches_util.deep_csv({arr}, {P}, '{f}', {self._D})"))
            elif dt == "reference":
                cols.append(
                    (
                        f,
                        f"arches_util.deep_csv_nested({arr}, {P}, '{f}', 'label', {self._D}, {self._ID})",
                    )
                )
                cols.append(
                    (
                        f"{f}_ids",
                        f"arches_util.deep_csv_nested({arr}, {P}, '{f}', 'list_item_id', {self._D}, {self._ID})",
                    )
                )
            elif dt == "resource-instance":
                cols.append(
                    (f, f"arches_util.deep_res_csv({arr}, {P}, '{f}', {self._D})")
                )
                cols.append(
                    (f"{f}_ids", f"arches_util.deep_csv({arr}, {P}, '{f}', {self._D})")
                )
            elif dt == "resource-instance-list":
                cols.append(
                    (
                        f,
                        f"arches_util.deep_res_csv_nested({arr}, {P}, '{f}', {self._D}, {self._ID})",
                    )
                )
                cols.append(
                    (
                        f"{f}_ids",
                        f"arches_util.deep_csv_nested({arr}, {P}, '{f}', NULL, {self._D}, {self._ID})",
                    )
                )
            elif dt == "file-list":
                cols.append(
                    (
                        f,
                        f"arches_util.deep_csv_nested({arr}, {P}, '{f}', 'name', {self._D}, {self._ID})",
                    )
                )
                cols.append(
                    (
                        f"{f}_file_ids",
                        f"arches_util.deep_csv_nested({arr}, {P}, '{f}', 'file_id', {self._D}, {self._ID})",
                    )
                )
            elif dt == "url":
                cols.append(
                    (f, f"arches_util.deep_url_csv({arr}, {P}, '{f}', {self._D})")
                )
                cols.append(
                    (
                        f"{f}_label",
                        f"arches_util.deep_csv_sub({arr}, {P}, '{f}', 'label', {self._D})",
                    )
                )

    def _build_table(self, root):
        """Build column list for a flat table. root=None → resource_flat."""
        cols = []
        members = [n for n in self.BY if self._grain_of(n) == root]
        for n in sorted(members, key=lambda x: len(self._chain(x))):
            if root is None:
                top = self._chain(n)[0]
                base = f"r.{top}"
                rel = self._n_depth(n)
                path_parts = self._obj_path(n, None)[1:]
            else:
                base = "g.t"
                rel = self._n_depth(n, root)
                path_parts = self._obj_path(n, root)

            if rel == 0:
                if root is None:
                    expr = base + "".join(f" -> '{x}'" for x in path_parts)
                else:
                    expr = base + "".join(f" -> '{x}'" for x in path_parts)
                self._emit_scalar(cols, n, expr)
            elif rel == 1:
                c = (
                    self._chain(n)
                    if root is None
                    else self._chain(n)[self._chain(n).index(root) + 1 :]
                )
                arr_ng = next(x for x in c if self._card(x) == "n")
                if root is None:
                    pre = self._chain(arr_ng)
                    arr = (
                        "r." + pre[0]
                        if len(pre) == 1
                        else "r." + pre[0] + "".join(f" -> '{x}'" for x in pre[1:])
                    )
                else:
                    pre = self._obj_path(arr_ng, root)
                    arr = base + "".join(f" -> '{x}'" for x in pre)
                after = self._chain(n)[self._chain(n).index(arr_ng) + 1 :]
                self._emit_csv(cols, n, arr, after)
                if not any(c0 == f"{arr_ng}_count" for c0, _ in cols):
                    cols.append(
                        (
                            f"{arr_ng}_count",
                            f"jsonb_array_length(arches_util.as_array({arr}))",
                        )
                    )
            # rel >= 2: n-within-n not supported in flat tables; silently skip.
        return cols

    def _grain_arr_expr(self, gname):
        c = self._chain(gname)
        if len(c) == 1:
            return f"r.{c[0]}"
        return "r." + c[0] + "".join(f" -> '{x}'" for x in c[1:])

    def _render_flat(self, name, cols, frm, extra_pk):
        sel = ",\n".join(f"    {e} AS {c}" for c, e in cols)
        idx = f"CREATE UNIQUE INDEX mv_{name}_pk ON {self.SC}.mv_{name} ({extra_pk});\n"
        return (
            f"DROP MATERIALIZED VIEW IF EXISTS {self.SC}.mv_{name} CASCADE;\n"
            f"CREATE MATERIALIZED VIEW {self.SC}.mv_{name} AS\n"
            f"{frm.format(sel=sel)}\n\n{idx}"
        )

    # -----------------------------------------------------------------------
    # Public: column introspection (for contract testing)
    # -----------------------------------------------------------------------
    def get_flat_columns(self, grain=None):
        """
        Return list of (col_name, flat_type) for the flat MV.
        flat_type: 'text' | 'boolean' | 'date' | 'numeric' | 'geometry'
        grain=None → resource_flat.
        """
        cols = self._build_table(grain)
        result = []
        for col, expr in cols:
            result.append((col, self._infer_flat_type(col, expr)))
        return result

    def get_all_flat_tables(self):
        """
        Return dict: {table_name: [(col_name, flat_type)]}.
        Includes resource_flat and all grain flat tables.
        Also includes geom columns for resource_flat.
        """
        geom_cols = []
        for _, f, _ in self.GEOMS:
            geom_cols += [
                (f"{f}_geom", "geometry"),
                (f"{f}_geom_type", "text"),
                (f"{f}_source_valid", "boolean"),
                (f"{f}_points", "geometry"),
                (f"{f}_lines", "geometry"),
                (f"{f}_polygons", "geometry"),
            ]
        tables = {
            "resource_flat": geom_cols + self.get_flat_columns(None),
        }
        for g in self.GRAINS:
            view_name = self._grain_view_name(g)
            tables[f"{view_name}_flat"] = self.get_flat_columns(g)
        return tables

    def _infer_flat_type(self, col, expr):
        if "::numeric" in expr and "arches_util" not in expr:
            return "numeric"
        if "::boolean" in expr and "arches_util" not in expr:
            return "boolean"
        if "::date" in expr and "arches_util" not in expr:
            return "date"
        return "text"

    # -----------------------------------------------------------------------
    # File headers
    # -----------------------------------------------------------------------
    def _stack_head(self):
        return (
            f"-- GENERATED by manage.py generate_databc_views - do not edit.\n"
            f"-- Graph {self.GRAPH_ID}\n"
            f"-- Requires 00_arches_util.sql to be applied first.\n"
            f"--\n"
            f"-- INVARIANTS:\n"
            f"--   * every key ALWAYS present; null, never absent.\n"
            f"--   * cardinality-n children are ALWAYS a jsonb array, [] when empty.\n"
            f"--   * cardinality-1 branches are an object, or null.\n"
            f"--   * array order is tiles.sortorder, then tileid.\n\n"
            f"SET client_min_messages = warning;\n"
            f"SET maintenance_work_mem = '512MB';\n"
            f"SET work_mem             = '128MB';\n\n"
            f"CREATE SCHEMA IF NOT EXISTS {self.SC};\n\n"
        )

    def _flat_head(self):
        return (
            f"-- GENERATED by manage.py generate_databc_views - do not edit.\n"
            f"-- Requires {self.SC}/mv_resource.sql to be applied first.\n"
            f"--\n"
            f"-- CONTRACT:\n"
            f"--   * cardinality-1 fields: REAL TYPES (date, numeric, boolean, text)\n"
            f"--   * cardinality-n fields: TEXT CSV (' | ' between tiles, '; ' within)\n"
            f"--   * POSITIONAL ALIGNMENT: null elements emit empty slots.\n"
            f"--   * references: x (labels) + x_ids pairs.\n\n"
            f"SET client_min_messages = warning;\n\n"
        )

    # -----------------------------------------------------------------------
    # Helpers for writing procedures
    # -----------------------------------------------------------------------
    def _refresh_proc(self, proc_name, mvs):
        return (
            f"-- GENERATED by manage.py generate_databc_views - do not edit.\n\n"
            f"CREATE OR REPLACE PROCEDURE {self.SC}.{proc_name}(concurrent boolean DEFAULT true)\n"
            f"LANGUAGE plpgsql AS $$\n"
            f"DECLARE\n"
            f"    mode text := CASE WHEN concurrent THEN 'CONCURRENTLY' ELSE '' END;\n"
            f"    mv   text;\n"
            f"BEGIN\n"
            f"    FOREACH mv IN ARRAY ARRAY[\n"
            + ",\n".join(f"        '{m}'" for m in mvs)
            + "\n"
            "    ]\n"
            "    LOOP\n"
            "        RAISE NOTICE 'refreshing %', mv;\n"
            "        EXECUTE format('REFRESH MATERIALIZED VIEW %s %s', mode, mv);\n"
            "        COMMIT;\n"
            "    END LOOP;\n"
            "END $$;\n"
        )

    def _alignment_test(self, res_cols, grain_tables):
        tabs = [("resource_flat", res_cols)] + [
            (f"{self._grain_view_name(g)}_flat", c) for g, c in grain_tables
        ]
        parts = []
        for tname, cols in tabs:
            groups = defaultdict(list)
            counts = {}
            for c, e in cols:
                m = re.match(
                    r"arches_util\.(deep_csv\w*|deep_res_csv\w*|deep_url_csv)"
                    r"\((.+?),\s*('\{[^}]*\}'::text\[\])",
                    e,
                )
                if m:
                    groups[(m.group(2).strip(), m.group(3))].append(c)
                m2 = re.match(
                    r"jsonb_array_length\(arches_util\.as_array\((.+?)\)\)$", e
                )
                if m2:
                    counts[m2.group(1).strip()] = c
            for (arr, _path), cs in groups.items():
                if arr not in counts:
                    continue
                cnt = counts[arr]
                parts.append(
                    f"  SELECT resourceinstanceid, {cnt} AS n, "
                    f"'{tname}.{cnt[:-6]}' AS grp,\n"
                    f"         ARRAY["
                    + ",\n               ".join(f"arches_util.nslots({c})" for c in cs)
                    + "] AS slots,\n"
                    f"         ARRAY["
                    + ", ".join(f"'{c}'" for c in cs)
                    + f"]::text[] AS colnames\n"
                    f"  FROM {self.SC}.mv_{tname} WHERE {cnt} > 0"
                )
        if not parts:
            return "-- No alignment groups found (no cardinality-n nodegroups with children).\n"
        return (
            "-- Alignment regression test. EXPECT ZERO ROWS.\n"
            "-- Run manually after a full generate + refresh.\n\n"
            "WITH v AS (\n" + "\n  UNION ALL\n".join(parts) + "\n)\n"
            "SELECT grp, colname,\n"
            "       count(DISTINCT resourceinstanceid) AS rows_affected,\n"
            "       count(*)                           AS bad_cells\n"
            "FROM v, LATERAL unnest(slots, colnames) AS u(sl, colname)\n"
            "WHERE sl IS DISTINCT FROM n\n"
            "GROUP BY grp, colname\n"
            "ORDER BY rows_affected DESC, grp, colname;\n"
        )

    def _write(self, filename, content):
        path = os.path.join(self.schema_dir, filename)
        with open(path, "w") as fh:
            fh.write(content)

    # -----------------------------------------------------------------------
    # Public: generate all SQL files
    # -----------------------------------------------------------------------
    def generate(self):
        """
        Write all SQL files for this graph.
        Returns a dict of generation metadata used by the command.
        """
        os.makedirs(self.schema_dir, exist_ok=True)
        head = self._stack_head()

        # Branch MVs (one file per top-level nodegroup)
        for n in self.TOPS:
            self._write(f"mv_{n}.sql", head + self._branch_mv_sql(n))

        # Geom MVs
        for ng, fname, nid in self.GEOMS:
            self._write(
                f"mv_geom_{fname}.sql",
                head + self._geom_mv_sql(fname, nid, self._ngid(ng)),
            )

        # Final stack MV
        self._write("mv_resource.sql", head + self._final_mv_sql())

        # Wrapper view (stable read contract)
        self._write(
            "resource_view.sql",
            f"-- GENERATED by manage.py generate_databc_views - do not edit.\n\n"
            f"CREATE OR REPLACE VIEW {self.SC}.resource AS SELECT * FROM {self.SC}.mv_resource;\n\n"
            f"COMMENT ON VIEW {self.SC}.resource IS\n"
            f"'Stable read contract for {self.SC}. One row per resource instance. "
            f"Backed by mv_resource.';\n\n"
            f"-- GRANT SELECT ON {self.SC}.resource TO <app_role>;\n",
        )

        # Refresh procedure (stack)
        refresh_mvs = (
            [f"{self.SC}.mv_geom_{f}" for _, f, _ in self.GEOMS]
            + [f"{self.SC}.mv_{n}" for n in self.TOPS]
            + [f"{self.SC}.mv_resource"]
        )
        self._write(
            "refresh_resource.sql", self._refresh_proc("refresh_resource", refresh_mvs)
        )

        # Flat MV
        flat_head = self._flat_head()
        res_cols = self._build_table(None)
        geom_cols_sql = "".join(
            f"    r.{f}_geom,\n    r.{f}_geom_type,\n    r.{f}_source_valid,\n"
            f"    r.{f}_points,\n    r.{f}_lines,\n    r.{f}_polygons,\n"
            for _, f, _ in self.GEOMS
        )
        res_flat_body = self._render_flat(
            "resource_flat",
            res_cols,
            "SELECT\n    r.resourceinstanceid,\n" + geom_cols_sql + "{sel}\n"
            f"FROM {self.SC}.mv_resource r;",
            "resourceinstanceid",
        )
        for _, f, _ in self.GEOMS:
            res_flat_body += (
                f"CREATE INDEX mv_resource_flat_{f}_gix"
                f" ON {self.SC}.mv_resource_flat USING GIST ({f}_geom);\n"
            )
        self._write("mv_resource_flat.sql", flat_head + res_flat_body)

        # Grain flat MVs
        grain_tables = []
        for gname in self.GRAINS:
            gcols = self._build_table(gname)
            grain_tables.append((gname, gcols))
            # Index columns use the stable view name so vw_*.sql JOIN keys match.
            vname = self._grain_view_name(gname)
            par = self._parent(gname)
            pg = self._grain_of(par) if par else None
            if pg is None:
                frm = (
                    f"SELECT\n    r.resourceinstanceid,\n"
                    f"    g.ord AS {vname}_index,\n{{sel}}\n"
                    f"FROM {self.SC}.mv_resource r,\n"
                    f"     LATERAL jsonb_array_elements(arches_util.as_array({self._grain_arr_expr(gname)}))\n"
                    f"             WITH ORDINALITY AS g(t, ord);"
                )
                pk = f"resourceinstanceid, {vname}_index"
            else:
                pre = self._obj_path(gname, pg)
                inner = "p.t" + "".join(f" -> '{x}'" for x in pre)
                frm = (
                    f"SELECT\n    r.resourceinstanceid,\n"
                    f"    p.ord AS {self._grain_view_name(pg)}_index,\n"
                    f"    g.ord AS {vname}_index,\n{{sel}}\n"
                    f"FROM {self.SC}.mv_resource r,\n"
                    f"     LATERAL jsonb_array_elements(arches_util.as_array({self._grain_arr_expr(pg)}))\n"
                    f"             WITH ORDINALITY AS p(t, ord),\n"
                    f"     LATERAL jsonb_array_elements(arches_util.as_array({inner}))\n"
                    f"             WITH ORDINALITY AS g(t, ord);"
                )
                pk = f"resourceinstanceid, {self._grain_view_name(pg)}_index, {vname}_index"
            mv_name = f"{gname}_flat"
            self._write(
                f"mv_{gname}_flat.sql",
                flat_head + self._render_flat(mv_name, gcols, frm, pk),
            )

        # Flat wrapper views (use stable view_names)
        wraps = [("resource_flat", "resource_flat")] + [
            (f"{self._grain_view_name(g)}_flat", f"{g}_flat") for g in self.GRAINS
        ]
        fv = "-- GENERATED by manage.py generate_databc_views - do not edit.\n\n"
        for w, m in wraps:
            fv += f"CREATE OR REPLACE VIEW {self.SC}.{w} AS SELECT * FROM {self.SC}.mv_{m};\n"
        fv += (
            f"\nCOMMENT ON VIEW {self.SC}.resource_flat IS\n"
            f"'Flat {self.SC} records, one row per resource. "
            f"Cardinality-n values are delimiter-joined text "
            f'(" | " between tiles, "; " within a tile).\';\n'
        )
        self._write("flat_views.sql", fv)

        # Refresh procedure (flat)
        refresh_flat_mvs = [f"{self.SC}.mv_{m}" for _, m in wraps]
        self._write(
            "refresh_flat.sql", self._refresh_proc("refresh_flat", refresh_flat_mvs)
        )

        # Alignment test (run manually after refresh)
        self._write("alignment_test.sql", self._alignment_test(res_cols, grain_tables))

        # Sanity check: no duplicate columns
        names = [c for c, _ in res_cols]
        dupes = sorted({c for c in names if names.count(c) > 1})
        if dupes:
            raise ValueError(
                f"Duplicate columns in resource_flat for {self.SC}: {dupes}"
            )

        return {
            "slug": self.SLUG,
            "schema": self.SC,
            "graph_id": self.GRAPH_ID,
            "tops": list(self.TOPS),
            "geoms": list(self.GEOMS),
            "grains": list(self.GRAINS),
            "grain_view_names": dict(self.GRAIN_VIEW_NAMES),
            "grain_tables": grain_tables,
            "res_cols": res_cols,
        }
