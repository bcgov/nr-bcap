"""
Management command: generate_databc_views

One-stop command for regenerating the DataBC materialized view SQL.

Spec files live in:  migrations/databc/{sv,as}_spec.py
Common SQL lives in: migrations/databc/00_common.sql
Output goes to:      migrations/sql/materialized_views/

Usage:
    # Regenerate SQL from existing specs (most common after a manual spec edit):
    python manage.py generate_databc_views
    python manage.py generate_databc_views [ sv | as | per | pub | rep ]

    # Regenerate specs from the live database, THEN regenerate SQL:
    python manage.py generate_databc_views --from-db
    python manage.py generate_databc_views --from-db [ sv | as | per | pub | rep ]

Workflow when the Arches graph model changes:
    1. Run with --from-db to pull the current node/nodegroup structure from the DB.
    2. Review the updated spec file in migrations/databc/.
       - Confirm cardinality against node_groups.cardinality.
       - Adjust FLAT_GRAINS if any cardinality-n nodegroups were added under other n groups.
       - Check date formats.
    3. Re-run WITHOUT --from-db to regenerate the SQL (or it runs automatically after step 1).
    4. Review the generated SQL in migrations/sql/materialized_views/.
    5. Create a new migration (django_migrate_sql detects the diff via makemigrations).
    6. Commit specs, SQL, and migration together.

This command handles the full DataBC workflow end-to-end.
"""

import os
import shutil
import subprocess
import sys
from collections import defaultdict, deque

from django.core.management.base import BaseCommand, CommandError

from arches.app.models.models import GraphModel, Node, NodeGroup

# Maps the DataBC short slug used by this command to the Arches graph slug
# stored in GraphModel.slug.  Update this if graph slugs change in the DB.
GRAPH_SLUGS = {
    "sv": "site-visit",
    "as": "archaeological-site",
    "rep": "repository",
    "pub": "publication",
    "per": "hca_permit",
}

DATE_FORMAT_DEFAULT = "YYYY-MM-DD"
DATE_DT = frozenset({"date"})
SEMANTIC_DT = "semantic"


class Command(BaseCommand):
    help = (
        "Generate DataBC materialized view SQL from spec files in "
        "migrations/databc/ and write output to migrations/sql/materialized_views/. "
        "Use --from-db to regenerate specs from the live database first."
    )

    KNOWN_GRAPHS = tuple(GRAPH_SLUGS.keys())  # ("sv", "as")

    def add_arguments(self, parser):
        parser.add_argument(
            "graphs",
            nargs="*",
            metavar="GRAPH",
            help=(
                "Graph slugs to process: sv (site_visit), as (archaeological_site). "
                "Defaults to all known graphs."
            ),
        )
        parser.add_argument(
            "--from-db",
            action="store_true",
            help=(
                "Regenerate spec files from the live database before generating SQL. "
                "Requires a working database connection."
            ),
        )

    def handle(self, *args, **options):
        graphs = options["graphs"] or list(self.KNOWN_GRAPHS)

        unknown = [g for g in graphs if g not in self.KNOWN_GRAPHS]
        if unknown:
            raise CommandError(
                f"Unknown graph slug(s): {', '.join(unknown)}. "
                f"Known: {', '.join(self.KNOWN_GRAPHS)}"
            )

        # Locate directories
        cmd_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(os.path.dirname(cmd_dir))
        mig_dir = os.path.join(app_dir, "migrations")
        spec_dir = os.path.join(mig_dir, "databc")
        out_dir = os.path.join(mig_dir, "sql", "materialized_views")
        os.makedirs(out_dir, exist_ok=True)

        # 1. Optionally regenerate specs from the live database
        if options["from_db"]:
            for slug in graphs:
                self._regenerate_spec(slug, spec_dir)

        # 2. Copy the static common SQL
        src = os.path.join(spec_dir, "00_common.sql")
        dst = os.path.join(out_dir, "00_arches_util.sql")
        shutil.copy2(src, dst)
        self.stdout.write(
            f"  copied 00_common.sql -> sql/materialized_views/00_arches_util.sql"
        )

        # 3. Generate stack + flat SQL for each requested graph
        generate_script = os.path.join(spec_dir, "generate.py")
        for slug in graphs:
            self.stdout.write(f"\nGenerating SQL for '{slug}' ...")
            result = subprocess.run(
                [sys.executable, generate_script, f"{slug}_spec", out_dir],
                cwd=spec_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise CommandError(f"generate.py failed for '{slug}':\n{result.stderr}")
            if result.stdout.strip():
                self.stdout.write(result.stdout.rstrip())
            self.stdout.write(self.style.SUCCESS(f"  [OK] {slug}"))

        self.stdout.write(self.style.SUCCESS(f"\nOutput written to:\n  {out_dir}"))
        self.stdout.write(
            "\nNext steps:\n"
            "  1. Review the generated SQL files in migrations/sql/materialized_views/.\n"
            "  2. Run manage.py makemigrations to generate AlterSQL migrations for any changes.\n"
            "  3. Commit specs, SQL, and migration together."
        )

    # ------------------------------------------------------------------
    # Spec generation from live database (--from-db)
    # ------------------------------------------------------------------

    def _regenerate_spec(self, slug, spec_dir):
        """Query the live DB for the graph and write an updated spec.py."""
        arches_slug = GRAPH_SLUGS[slug]
        self.stdout.write(
            f"\nRegenerating spec for '{slug}' (graph slug: {arches_slug}) ..."
        )

        try:
            graph = GraphModel.objects.get(slug=arches_slug)
        except GraphModel.DoesNotExist:
            raise CommandError(
                f"No graph found with slug '{arches_slug}'. "
                "Check GRAPH_SLUGS in this command or the DB."
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

        ng_alias = {}
        for ng_id, ng in ng_by_id.items():
            grouping = node_by_id.get(ng_id)
            ng_alias[ng_id] = grouping.alias if grouping else ng_id

        ng_fields = defaultdict(list)
        for node in nodes:
            if node.datatype == SEMANTIC_DT:
                continue
            ng_id = str(node.nodegroup_id)
            if ng_id == root_ng_id:
                continue
            datefmt = self._date_format(node) if node.datatype in DATE_DT else None
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
                    f"  Warning: nodegroup '{ng_alias.get(ng_id, ng_id)}' unreachable, skipped."
                )
            )

        # Load existing spec to preserve SLUG and FLAT_GRAINS (not queryable from DB)
        existing = self._load_existing_spec(slug, spec_dir)
        spec_slug = existing.get("SLUG", slug)
        flat_grains = existing.get("FLAT_GRAINS", [])

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
                (alias, ng_id, parent_alias, ng.cardinality, ng_fields.get(ng_id, []))
            )

        content = self._render_spec(
            graph_id, graph.slug.replace("-", "_"), spec_slug, flat_grains, ng_list
        )
        out_path = os.path.join(spec_dir, f"{slug}_spec.py")
        with open(out_path, "w") as fh:
            fh.write(content)
        self._format_with_black(out_path)
        self.stdout.write(
            self.style.SUCCESS(f"  wrote {out_path} ({len(ng_list)} nodegroups)")
        )

        geom_nodes = [
            (f_alias, f_nid, ng_id)
            for alias, ng_id, _, _, fields in ng_list
            for f_alias, f_nid, dt, _ in fields
            if dt == "geojson-feature-collection"
        ]
        if geom_nodes:
            self.stdout.write(
                self.style.WARNING(
                    "  geojson-feature-collection nodes detected — verify geom_mv() calls in generate.py:"
                )
            )
            for g_alias, g_nid, g_ng_id in geom_nodes:
                self.stdout.write(f"    geom_mv('{g_alias}', '{g_nid}', '{g_ng_id}')")

    def _format_with_black(self, path):
        result = subprocess.run(
            [sys.executable, "-m", "black", "--quiet", path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.stderr.write(
                self.style.WARNING(
                    f"  black could not format {path}:\n{result.stderr.strip()}"
                )
            )

    def _date_format(self, node):
        cfg = node.config
        if isinstance(cfg, dict):
            fmt = cfg.get("dateFormat") or cfg.get("dateformat")
            if fmt:
                return fmt
        return DATE_FORMAT_DEFAULT

    def _load_existing_spec(self, slug, spec_dir):
        """Return a dict with SLUG and FLAT_GRAINS from the existing spec, if it exists."""
        import importlib.util

        path = os.path.join(spec_dir, f"{slug}_spec.py")
        if not os.path.exists(path):
            return {}
        spec = importlib.util.spec_from_file_location(f"_spec_{slug}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return {
            "SLUG": getattr(mod, "SLUG", slug),
            "FLAT_GRAINS": getattr(mod, "FLAT_GRAINS", []),
        }

    def _render_spec(self, graph_id, schema, slug, flat_grains, ng_list):
        lines = [
            '"""',
            f"{schema} graph spec.",
            "",
            "AUTO-GENERATED by `manage.py generate_databc_views --from-db`.",
            "Review cardinality, FLAT_GRAINS, and date formats before regenerating SQL.",
            '"""',
            "",
            f"GRAPH_ID = '{graph_id}'",
            f"SCHEMA   = '{schema}'",
            f"SLUG     = '{slug}'",
            "",
            f"FLAT_GRAINS = {flat_grains!r}",
            "",
            "# name, ngid, parent, cardinality, [(field, nodeid, dt, datefmt)]",
            "NG = [",
        ]
        for alias, ngid, parent_alias, card, fields in ng_list:
            parent_repr = f"'{parent_alias}'" if parent_alias is not None else "None"
            if not fields:
                lines.append(f"    ('{alias}', '{ngid}', {parent_repr}, '{card}', []),")
            else:
                lines.append(f"    ('{alias}', '{ngid}', {parent_repr}, '{card}', [")
                for f_alias, f_nodeid, f_dt, f_datefmt in fields:
                    datefmt_repr = f"'{f_datefmt}'" if f_datefmt else "None"
                    lines.append(
                        f"        ('{f_alias}', '{f_nodeid}', '{f_dt}', {datefmt_repr}),"
                    )
                lines.append("    ]),")
        lines.append("]")
        return "\n".join(lines) + "\n"
