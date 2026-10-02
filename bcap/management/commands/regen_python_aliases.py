"""
Management command: regen_python_aliases

Regenerates the node-alias files in bcap/util/aliases from the database.

For each graph that already has an alias file, writes one
``<GraphSlug>Aliases`` class with an ``ALIAS = "alias"`` constant per
non-semantic node. Only existing files are regenerated; new graphs are not
added automatically.

DB nodes absent from the package graph JSON (drift) are still written to the
alias file, but reported with a snippet to delete them from the DB.

Also regenerates the ``GraphIds`` class in bcap/util/bcap_aliases.py.

    manage.py regen_python_aliases                     # dev DB (default)
    manage.py regen_python_aliases --target test       # test_<name> DB (--keepdb)
    manage.py regen_python_aliases --new investigation # add a new graph
"""

import glob
import json
import os
import re
import subprocess

from django.core.management.base import BaseCommand

from arches.app.models import models as arches_models

# Paths are resolved relative to this file:
# commands/ -> management/ -> bcap/ -> nr-bcap/
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
_ALIAS_DIR = os.path.join(_REPO_ROOT, "bcap", "util", "aliases")
_BCAP_ALIASES_PATH = os.path.join(_REPO_ROOT, "bcap", "util", "bcap_aliases.py")
_GRAPHS_DIR = os.path.join(_REPO_ROOT, "bcap", "pkg", "graphs")


def _switch_to_test_db():
    """Point the default DB connection at the test database.

    Useful when the test runner was run with --keepdb and you want regen_python_aliases
    to read the same schema that tests see.
    """
    from django.conf import settings
    from django.db import connections

    default = settings.DATABASES["default"]
    test_name = (default.get("TEST") or {}).get("NAME") or f"test_{default['NAME']}"
    default["NAME"] = test_name
    connections["default"].close()
    print(f"targeting test database: {test_name}")


def _orphan_nodegroups():
    """Nodegroups with no nodes and no tiles -- safe to delete.

    A deleted node can orphan its nodegroup, whose cards then break graph
    imports. One with no nodes may still own tiles (resource data) that deletion
    would cascade away, so any with tiles are reported but not offered.
    """
    orphans = []
    for ng in arches_models.NodeGroup.objects.all():
        if arches_models.Node.objects.filter(nodegroup_id=ng.nodegroupid).exists():
            continue
        tile_count = arches_models.TileModel.objects.filter(
            nodegroup_id=ng.nodegroupid
        ).count()
        if tile_count:
            print(
                f"  ORPHAN nodegroup {ng.nodegroupid}: no nodes but {tile_count} "
                f"tile(s) -- NOT auto-deleted (would destroy resource data)"
            )
            continue
        print(f"  ORPHAN nodegroup {ng.nodegroupid}: no nodes, no tiles")
        orphans.append(ng)
    return orphans


def _json_aliases_by_slug():
    """Map each graph slug to the set of node aliases in its package JSON."""
    by_slug = {}
    for path in glob.glob(os.path.join(_GRAPHS_DIR, "**", "*.json"), recursive=True):
        try:
            with open(path) as graph_file:
                doc = json.load(graph_file)
        except (ValueError, OSError):
            continue
        graphs = doc.get("graph")
        if isinstance(graphs, dict):
            graphs = [graphs]
        for graph in graphs or []:
            slug = graph.get("slug")
            if not slug:
                continue
            by_slug.setdefault(slug, set()).update(
                node["alias"] for node in graph.get("nodes", []) if node.get("alias")
            )
    return by_slug


# Words whose camel-case form isn't just .title() (acronyms in class names).
_ACRONYMS = {"hca": "HCA"}


def _snake_to_camel(snake_str):
    return "".join(_ACRONYMS.get(word, word.title()) for word in snake_str.split("_"))


def _regen_graph_ids():
    """Regenerate the GraphIds class in bcap_aliases.py from the database.

    Queries all graphs with a slug and writes ``SLUG = "uuid"`` constants.
    Replaces an existing ``class GraphIds:`` block in-place, or appends one.
    """
    graphs = list(
        arches_models.Graph.objects.exclude(slug__isnull=True)
        .exclude(slug="")
        .filter(source_identifier__isnull=True)
        .filter(isresource=True)
        .values("slug", "graphid")
        .order_by("slug")
    )

    lines = ["class GraphIds:\n"]
    for graph in graphs:
        lines.append(f'    {graph["slug"].upper()} = "{graph["graphid"]}"\n')
    class_block = "".join(lines)

    with open(_BCAP_ALIASES_PATH) as f:
        content = f.read()

    pattern = r"class GraphIds:.*?(?=\n\nclass |\Z)"
    if re.search(pattern, content, re.DOTALL):
        new_content = re.sub(
            pattern, class_block.rstrip("\n"), content, flags=re.DOTALL
        )
    else:
        new_content = content.rstrip("\n") + "\n\n\n" + class_block

    with open(_BCAP_ALIASES_PATH, "w") as f:
        f.write(new_content)

    print(f"GraphIds -> {_BCAP_ALIASES_PATH} ({len(graphs)} graphs)")


def _run_black(paths):
    """Run black on the given file paths, if black is available."""
    try:
        subprocess.run(["black"] + paths, check=True)
    except FileNotFoundError:
        print("WARNING: black not found on PATH; skipping formatting")


def _write_alias_class(alias_file, classname, nodes):
    alias_file.write(f"class {classname}(AbstractAliases):\n")
    for node in nodes:
        alias_file.write(f'    {node.alias.upper()} = "{node.alias}"\n')
    alias_file.write(
        f"\n    @staticmethod\n"
        f"    def get_aliases():\n"
        f"        return AbstractAliases.get_dict({classname})\n"
    )


def _create_alias_file(slug, json_aliases):
    nodes = (
        arches_models.Node.objects.filter(graph__slug=slug)
        .filter(graph__source_identifier__isnull=True)
        .exclude(alias__isnull=True)
        .prefetch_related("graph")
        .order_by("graph__slug", "alias")
        .all()
    )

    # Report drift (DB nodes not in the graph JSON) but still write them, so the
    # alias file mirrors the DB until the DB is fixed.
    json_for_slug = json_aliases.get(slug)
    drift_nodes = []
    if json_for_slug is None:
        print(f"  WARNING: no package JSON for slug {slug!r}; drift not checked")
    else:
        drift_nodes = sorted(
            (n for n in nodes if n.alias not in json_for_slug), key=lambda n: n.alias
        )
        for node in drift_nodes:
            print(f"  DRIFT {slug}.{node.alias}: in DB but not in graph JSON")

    # Value nodes go in <Graph>Aliases; grouping/collector nodes (the nodegroup
    # keys used in aliased_data payloads -- nodeid == nodegroup_id, no value of
    # their own) go in <Graph>GroupAliases. Non-collector semantic nodes are
    # dropped: they carry neither a value nor a key.
    value_nodes = [n for n in nodes if n.datatype != "semantic"]
    group_nodes = [
        n for n in nodes if n.datatype == "semantic" and n.pk == n.nodegroup_id
    ]

    filename = os.path.join(_ALIAS_DIR, slug + ".py")
    base = _snake_to_camel(slug)
    print(
        f"{slug} -> {filename} "
        f"({len(value_nodes)} value, {len(group_nodes)} group nodes)"
    )
    with open(filename, "w") as alias_file:
        alias_file.write("from bcap.util.bcap_aliases import AbstractAliases\n\n\n")
        _write_alias_class(alias_file, base + "Aliases", value_nodes)
        alias_file.write("\n\n")
        _write_alias_class(alias_file, base + "GroupAliases", group_nodes)
    return drift_nodes


def _print_drift_fix(drift_nodes, orphan_nodegroups):
    """Print a self-contained snippet that deletes the drift nodes and orphan
    nodegroups (with their dangling cards). Review before running."""
    if not drift_nodes and not orphan_nodegroups:
        return
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "bcap.settings")
    print("\n" + "=" * 72)
    print(
        f"DRIFT FIX: {len(drift_nodes)} node(s) not in any graph JSON, "
        f"{len(orphan_nodegroups)} nodegroup(s) with no nodes."
    )
    print("!!! BACK UP YOUR DATABASE BEFORE RUNNING THESE COMMANDS !!!")
    print("Run this to delete them (review first):\n")
    print("python3 <<'PY'")
    print("import os, django")
    print(f'os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{settings_module}")')
    print("django.setup()")
    print("from arches.app.models.models import CardModel, Node, NodeGroup")
    if drift_nodes:
        print("Node.objects.filter(pk__in=[")
        for slug, node in drift_nodes:
            print(f'    "{node.pk}",  # {slug}.{node.alias}')
        print("]).delete()")
    if orphan_nodegroups:
        print("orphan_nodegroups = [")
        for ng in orphan_nodegroups:
            print(f'    "{ng.nodegroupid}",')
        print("]")
        print("CardModel.objects.filter(nodegroup_id__in=orphan_nodegroups).delete()")
        print("NodeGroup.objects.filter(nodegroupid__in=orphan_nodegroups).delete()")
    print("PY")
    print("=" * 72)


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "--target",
            choices=["dev", "test"],
            default="dev",
            help="Which database to read: the local dev DB or the test DB (default: dev)",
        )
        parser.add_argument(
            "--new",
            nargs="+",
            default=[],
            metavar="SLUG",
            help="Also create alias files for these graph slugs (new graphs that "
            "don't have a file yet)",
        )

    def handle(self, *args, **options):
        if options["target"] == "test":
            _switch_to_test_db()

        _regen_graph_ids()
        orphan_nodegroups = _orphan_nodegroups()

        # Regenerate alias files that already exist, plus any --new slugs.
        existing = sorted(
            set(
                f[:-3]
                for f in os.listdir(_ALIAS_DIR)
                if f.endswith(".py") and f != "__init__.py"
            )
            | set(options["new"])
        )
        slugs_present = set(
            arches_models.Graph.objects.filter(slug__in=existing).values_list(
                "slug", flat=True
            )
        )
        json_aliases = _json_aliases_by_slug()
        all_drift = []
        written_files = [_BCAP_ALIASES_PATH]
        for slug in existing:
            if slug in slugs_present:
                drift_nodes = _create_alias_file(slug, json_aliases)
                all_drift.extend((slug, node) for node in drift_nodes)
                written_files.append(os.path.join(_ALIAS_DIR, slug + ".py"))
            else:
                print(f"SKIP {slug}: no graph with that slug in the DB")
        _run_black(written_files)
        _print_drift_fix(all_drift, orphan_nodegroups)
