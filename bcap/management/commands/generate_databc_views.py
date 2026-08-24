"""
Management command: generate_databc_views

Generates DataBC materialized view SQL from the live database graph model.
Always reads node/nodegroup structure from the database — no spec files used as input.

Workflow:
    1. Run manage.py generate_databc_views [sv|as|per|pub|rep]
    2. Review generated SQL in migrations/sql/materialized_views/
    3. Run manage.py test tests.test_databc_contract
    4. Run manage.py makemigrations to generate AlterSQL migrations
    5. Commit SQL + databc_sql_items.py + migrations together

Graph slugs are defined in bcap/databc_config.py. Edit that file to:
    - Add/remove graphs
    - Change flat_grains (which cardinality-n nodegroups get their own grain table)
    - Set view_names overrides to keep wrapper view names stable across renames
"""

import os
import shutil
import types
from collections import defaultdict, deque

from django.core.management.base import BaseCommand, CommandError

from arches.app.models.models import GraphModel, Node, NodeGroup

from bcap.databc_config import GRAPHS
from bcap.migrations.databc.generator import SpecGenerator

_DATE_FORMAT_DEFAULT = "YYYY-MM-DD"
_DATE_DT = frozenset({"date"})
_SEMANTIC_DT = "semantic"

# Maps arches_slug → DataBC API view config (static files, never generated).
# Update here if new vw_*.sql files are added.
_API_VIEWS = {
    "site_visit": {
        "item_name": "databc_site_visit",
        "vw_file": "vw_site_visit",
        "drops": ["databc.vw_site_visit", "databc.vw_site_visit_location"],
    },
    "archaeological_site": {
        "item_name": "databc_archaeological_site",
        "vw_file": "vw_archaeological_site",
        "drops": [
            "databc.vw_archaeological_site",
            "databc.vw_archaeological_site_site_location",
            "databc.vw_archaeological_site_bc_property_address",
        ],
    },
    "hca_permit": {
        "item_name": "databc_hca_permit",
        "vw_file": "vw_hca_permit",
        "drops": ["databc.vw_hca_permit"],
    },
    "publication": {
        "item_name": "databc_publication",
        "vw_file": "vw_publication",
        "drops": ["databc.vw_publication"],
    },
    "repository": {
        "item_name": "databc_repository",
        "vw_file": "vw_repository",
        "drops": ["databc.vw_repository"],
    },
}


class Command(BaseCommand):
    help = (
        "Generate DataBC materialized view SQL from the live database. "
        "Always reads node/nodegroup structure from the DB. "
        "Output goes to migrations/sql/materialized_views/ and bcap/databc_sql_items.py."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "graphs",
            nargs="*",
            metavar="GRAPH",
            help=(
                f"Graph short slugs to process ({', '.join(GRAPHS)}). "
                "Defaults to all."
            ),
        )

    def handle(self, *args, **options):
        graphs = options["graphs"] or list(GRAPHS.keys())

        unknown = [g for g in graphs if g not in GRAPHS]
        if unknown:
            raise CommandError(
                f"Unknown graph slug(s): {', '.join(unknown)}. "
                f"Known: {', '.join(GRAPHS)}"
            )

        cmd_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(os.path.dirname(cmd_dir))
        mig_dir = os.path.join(app_dir, "migrations")
        spec_dir = os.path.join(mig_dir, "databc")
        out_dir = os.path.join(mig_dir, "sql", "materialized_views")
        os.makedirs(out_dir, exist_ok=True)

        # Copy shared arches_util SQL
        src = os.path.join(spec_dir, "00_common.sql")
        dst = os.path.join(out_dir, "00_arches_util.sql")
        shutil.copy2(src, dst)
        self.stdout.write(
            "  copied 00_common.sql -> sql/materialized_views/00_arches_util.sql"
        )

        # Generate SQL for each requested graph
        all_results = {}
        for slug in graphs:
            self.stdout.write(f"\nGenerating SQL for '{slug}' ...")
            cfg = GRAPHS[slug]
            spec = self._build_spec(slug, cfg)
            gen = SpecGenerator(spec, out_dir)
            result = gen.generate()
            all_results[slug] = result
            self.stdout.write(
                self.style.SUCCESS(
                    f"  [OK] {slug} ({len(spec.NG)} nodegroups, "
                    f"{len(result['tops'])} branch MVs)"
                )
            )

        # Always regenerate databc_sql_items.py for the full GRAPHS set.
        # If only a subset was requested, we still need the full list so the
        # generated file stays consistent. Re-run all slugs that aren't already done.
        if set(graphs) != set(GRAPHS.keys()):
            self.stdout.write(
                "\nRegenerating remaining graphs for sql_items consistency ..."
            )
            for slug in GRAPHS:
                if slug not in all_results:
                    cfg = GRAPHS[slug]
                    try:
                        spec = self._build_spec(slug, cfg)
                        gen = SpecGenerator(spec, out_dir)
                        result = gen.generate()
                        all_results[slug] = result
                        self.stdout.write(f"  [OK] {slug}")
                    except CommandError as exc:
                        self.stderr.write(
                            self.style.WARNING(
                                f"  WARNING: could not regenerate '{slug}': {exc}. "
                                "Skipping from sql_items."
                            )
                        )

        items_path = os.path.join(app_dir, "databc_sql_items.py")
        self._write_sql_items(items_path, all_results)
        self.stdout.write(self.style.SUCCESS(f"\nUpdated: {items_path}"))

        self.stdout.write(self.style.SUCCESS(f"\nOutput written to:\n  {out_dir}"))
        self.stdout.write(
            "\nNext steps:\n"
            "  1. Review generated SQL in migrations/sql/materialized_views/.\n"
            "  2. Run:  python manage.py test tests.test_databc_contract\n"
            "  3. Run:  python manage.py makemigrations\n"
            "  4. Commit SQL + databc_sql_items.py + migrations together."
        )

    # ------------------------------------------------------------------
    # Build spec object from DB + databc_config
    # ------------------------------------------------------------------

    def _build_spec(self, slug, cfg):
        arches_slug = cfg["arches_slug"]
        flat_grains = cfg["flat_grains"]
        view_names = cfg.get("view_names", {})
        schema = arches_slug.replace("-", "_")

        try:
            graph = GraphModel.objects.get(slug=arches_slug)
        except GraphModel.DoesNotExist:
            raise CommandError(
                f"No graph found with slug '{arches_slug}' (for '{slug}'). "
                "Check databc_config.py or the DB."
            )

        graph_id = str(graph.graphid)
        self.stdout.write(f"  graph_id: {graph_id}")

        nodes = list(
            Node.objects.filter(graph=graph)
            .select_related("nodegroup")
            .order_by("sortorder", "nodeid")
        )
        node_by_id = {str(n.nodeid): n for n in nodes}

        root_nodes = [n for n in nodes if n.istopnode]
        if not root_nodes:
            raise CommandError(f"Graph '{arches_slug}' has no top node.")
        root_ng_id = str(root_nodes[0].nodegroup_id)

        all_ngs = list(
            NodeGroup.objects.filter(node__graph=graph)
            .distinct()
            .select_related("parentnodegroup")
        )
        ng_by_id = {str(ng.nodegroupid): ng for ng in all_ngs}

        ng_alias = {
            ng_id: (node_by_id[ng_id].alias if ng_id in node_by_id else ng_id)
            for ng_id in ng_by_id
        }

        ng_fields = defaultdict(list)
        for node in nodes:
            if node.datatype == _SEMANTIC_DT:
                continue
            ng_id = str(node.nodegroup_id)
            if ng_id == root_ng_id:
                continue
            datefmt = self._date_format(node) if node.datatype in _DATE_DT else None
            ng_fields[ng_id].append(
                (node.alias, str(node.nodeid), node.datatype, datefmt)
            )

        children = defaultdict(list)
        tops = []
        for ng_id in ng_by_id:
            if ng_id == root_ng_id:
                continue
            ng = ng_by_id[ng_id]
            parent_id = str(ng.parentnodegroup_id) if ng.parentnodegroup_id else None
            if parent_id is None or parent_id == root_ng_id:
                tops.append(ng_id)
            else:
                children[parent_id].append(ng_id)

        ordered = []
        queue = deque(tops)
        while queue:
            ng_id = queue.popleft()
            ordered.append(ng_id)
            queue.extend(children.get(ng_id, []))

        skipped = [
            ng_id
            for ng_id in ng_by_id
            if ng_id != root_ng_id and ng_id not in set(ordered)
        ]
        for ng_id in skipped:
            self.stderr.write(
                self.style.WARNING(
                    f"  Warning: nodegroup '{ng_alias.get(ng_id, ng_id)}' "
                    "is unreachable (no valid parent chain); skipped."
                )
            )

        new_aliases = {ng_alias[ng_id] for ng_id in ordered}
        invalid_grains = [g for g in flat_grains if g not in new_aliases]
        if invalid_grains:
            raise CommandError(
                f"flat_grains in databc_config.py for '{slug}' references unknown "
                f"nodegroup aliases: {invalid_grains}.\n"
                f"Known aliases: {sorted(new_aliases)}\n"
                "Update databc_config.py to match the current DB aliases."
            )

        ng_list = []
        for ng_id in ordered:
            ng = ng_by_id[ng_id]
            alias = ng_alias.get(ng_id, ng_id)
            parent_id = str(ng.parentnodegroup_id) if ng.parentnodegroup_id else None
            parent_alias = (
                None
                if parent_id is None or parent_id == root_ng_id
                else ng_alias.get(parent_id)
            )
            ng_list.append(
                (
                    alias,
                    ng_id,
                    parent_alias,
                    ng.cardinality,
                    ng_fields.get(ng_id, []),
                )
            )

        return types.SimpleNamespace(
            GRAPH_ID=graph_id,
            SCHEMA=schema,
            SLUG=slug,
            FLAT_GRAINS=flat_grains,
            FLAT_GRAIN_VIEW_NAMES=view_names,
            NG=ng_list,
        )

    def _date_format(self, node):
        cfg = node.config
        if isinstance(cfg, dict):
            fmt = cfg.get("dateFormat") or cfg.get("dateformat")
            if fmt:
                return fmt
        return _DATE_FORMAT_DEFAULT

    # ------------------------------------------------------------------
    # Write databc_sql_items.py
    # ------------------------------------------------------------------

    def _write_sql_items(self, items_path, all_results):
        ordered_slugs = [s for s in GRAPHS if s in all_results]
        L = []

        L += [
            "# GENERATED by manage.py generate_databc_views — do not edit.",
            "# Re-run the command after graph model or databc_config.py changes.",
            "",
            "from django_migrate_sql.config import SQLItem",
            "from bcap.migrations.util.migration_util import format_sql",
            "",
        ]

        # Dependency list variables
        for slug in ordered_slugs:
            r = all_results[slug]
            schema = r["schema"]
            tops = r["tops"]
            geoms = r["geoms"]
            grains = r["grains"]
            U = slug.upper()

            L.append(f"# {schema} dependency lists")
            L.append(f"_{U}_BRANCHES = [")
            for n in tops:
                L.append(f'    ("bcap", "{slug}_mv_{n}"),')
            L.append("]")

            L.append(f"_{U}_GEOMS = [")
            for _, fname, _ in geoms:
                L.append(f'    ("bcap", "{slug}_mv_geom_{fname}"),')
            L.append("]")

            L.append(f"_{U}_GRAIN_FLATS = [")
            for g in grains:
                L.append(f'    ("bcap", "{slug}_mv_{g}_flat"),')
            L.append("]")
            L.append("")

        # sql_items list
        L.append("sql_items = [")

        # Shared arches_util
        L += [
            "    # -------------------------------------------------------------------",
            "    # Shared arches_util schema (indexes + helper functions)",
            "    # -------------------------------------------------------------------",
            "    SQLItem(",
            '        "databc_arches_util",',
            '        format_sql("sql/materialized_views/00_arches_util.sql"),',
            "        reverse_sql=(",
            '            "DROP SCHEMA IF EXISTS arches_util CASCADE;\\n"',
            '            "DROP INDEX IF EXISTS public.tiles_nodegroupid_idx;\\n"',
            '            "DROP INDEX IF EXISTS public.geojson_geometries_nodeid_idx;\\n"',
            '            "DROP INDEX IF EXISTS public.resource_instances_graphid_idx;"',
            "        ),",
            "    ),",
        ]

        for slug in ordered_slugs:
            r = all_results[slug]
            schema = r["schema"]
            tops = r["tops"]
            geoms = r["geoms"]
            grains = r["grains"]
            gvn = r["grain_view_names"]
            U = slug.upper()

            L += [
                f"    # -------------------------------------------------------------------",
                f"    # {schema}",
                f"    # -------------------------------------------------------------------",
            ]

            # Branch MVs
            for n in tops:
                L += [
                    "    SQLItem(",
                    f'        "{slug}_mv_{n}",',
                    f'        format_sql("sql/materialized_views/{schema}/mv_{n}.sql"),',
                    f'        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS {schema}.mv_{n} CASCADE;",',
                    '        dependencies=[("bcap", "databc_arches_util")],',
                    "    ),",
                ]

            # Geom MVs
            for _, fname, _ in geoms:
                L += [
                    "    SQLItem(",
                    f'        "{slug}_mv_geom_{fname}",',
                    f'        format_sql("sql/materialized_views/{schema}/mv_geom_{fname}.sql"),',
                    f'        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS {schema}.mv_geom_{fname} CASCADE;",',
                    '        dependencies=[("bcap", "databc_arches_util")],',
                    "    ),",
                ]

            # Stack MV
            dep_expr = f"_{U}_BRANCHES + _{U}_GEOMS" if geoms else f"_{U}_BRANCHES"
            L += [
                "    SQLItem(",
                f'        "{slug}_mv_resource",',
                f'        format_sql("sql/materialized_views/{schema}/mv_resource.sql"),',
                f'        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS {schema}.mv_resource CASCADE;",',
                f"        dependencies={dep_expr},",
                "    ),",
            ]

            # Stable wrapper view
            L += [
                "    SQLItem(",
                f'        "{slug}_resource_view",',
                f'        format_sql("sql/materialized_views/{schema}/resource_view.sql"),',
                f'        reverse_sql="DROP VIEW IF EXISTS {schema}.resource;",',
                "        replace=True,",
                f'        dependencies=[("bcap", "{slug}_mv_resource")],',
                "    ),",
            ]

            # Refresh procedure (stack)
            L += [
                "    SQLItem(",
                f'        "{slug}_refresh_resource",',
                f'        format_sql("sql/materialized_views/{schema}/refresh_resource.sql"),',
                f'        reverse_sql="DROP PROCEDURE IF EXISTS {schema}.refresh_resource(boolean);",',
                "        replace=True,",
                f'        dependencies=[("bcap", "{slug}_mv_resource")],',
                "    ),",
            ]

            # Resource flat MV
            L += [
                "    SQLItem(",
                f'        "{slug}_mv_resource_flat",',
                f'        format_sql("sql/materialized_views/{schema}/mv_resource_flat.sql"),',
                f'        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS {schema}.mv_resource_flat CASCADE;",',
                f'        dependencies=[("bcap", "{slug}_mv_resource")],',
                "    ),",
            ]

            # Grain flat MVs (named after nodegroup alias)
            for g in grains:
                L += [
                    "    SQLItem(",
                    f'        "{slug}_mv_{g}_flat",',
                    f'        format_sql("sql/materialized_views/{schema}/mv_{g}_flat.sql"),',
                    f'        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS {schema}.mv_{g}_flat CASCADE;",',
                    f'        dependencies=[("bcap", "{slug}_mv_resource_flat")],',
                    "    ),",
                ]

            # Flat wrapper views (reverse drops use stable view_names)
            flat_wrappers = ["resource_flat"] + [
                f"{gvn.get(g, g)}_flat" for g in grains
            ]
            dep_flat = (
                f'[("bcap", "{slug}_mv_resource_flat")] + _{U}_GRAIN_FLATS'
                if grains
                else f'[("bcap", "{slug}_mv_resource_flat")]'
            )
            L.append("    SQLItem(")
            L.append(f'        "{slug}_flat_views",')
            L.append(
                f'        format_sql("sql/materialized_views/{schema}/flat_views.sql"),'
            )
            L.append("        reverse_sql=(")
            for v in flat_wrappers:
                L.append(f'            "DROP VIEW IF EXISTS {schema}.{v};\\n"')
            L.append("        ),")
            L.append("        replace=True,")
            L.append(f"        dependencies={dep_flat},")
            L.append("    ),")

            # Refresh procedure (flat)
            L += [
                "    SQLItem(",
                f'        "{slug}_refresh_flat",',
                f'        format_sql("sql/materialized_views/{schema}/refresh_flat.sql"),',
                f'        reverse_sql="DROP PROCEDURE IF EXISTS {schema}.refresh_flat(boolean);",',
                "        replace=True,",
                f"        dependencies={dep_flat},",
                "    ),",
            ]

        # Static API export views (vw_*.sql — never generated)
        L += [
            "    # -------------------------------------------------------------------",
            "    # DataBC API export views (static vw_*.sql — do not regenerate)",
            "    # -------------------------------------------------------------------",
        ]
        for slug in ordered_slugs:
            arches_slug = GRAPHS[slug]["arches_slug"]
            api = _API_VIEWS.get(arches_slug)
            if not api:
                continue
            L.append("    SQLItem(")
            L.append(f'        "{api["item_name"]}",')
            L.append(f'        format_sql("sql/views/databc/{api["vw_file"]}.sql"),')
            L.append("        reverse_sql=(")
            for d in api["drops"]:
                L.append(f'            "DROP VIEW IF EXISTS {d};\\n"')
            L.append("        ),")
            L.append("        replace=True,")
            L.append(f'        dependencies=[("bcap", "{slug}_flat_views")],')
            L.append("    ),")

        L.append("]")
        L.append("")

        with open(items_path, "w") as fh:
            fh.write("\n".join(L))
