#!/usr/bin/env python
"""Regenerate the node-alias files in bcap/util/aliases from the database.

For each graph that already has an alias file, writes one
``<GraphSlug>Aliases`` class with an ``ALIAS = "alias"`` constant per
non-semantic node. Only existing files are regenerated; new graphs are not
added automatically.

DB nodes absent from the package graph JSON (drift) are still written to the
alias file, but reported with a snippet to delete them from the DB.

Runs standalone (it bootstraps Django itself). Target either the local dev
database or the runner-created test database (test_<name>, e.g. with --keepdb):

    python3 tools/regen_aliases.py                 # dev DB (default)
    python3 tools/regen_aliases.py --target test   # test_<name> DB

Idea given from: Brett Ferguson
"""

import argparse
import glob
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIAS_DIR = os.path.join(REPO_ROOT, "bcap", "util", "aliases")
GRAPHS_DIR = os.path.join(REPO_ROOT, "bcap", "pkg", "graphs")


def _bootstrap_django(settings_module, target):
    """Put the repo on the path and initialize Django so the ORM is usable
    without manage.py. For the test target, point the default connection at the
    test database (the one the test runner builds, e.g. under --keepdb)."""
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

    import django

    django.setup()

    if target == "test":
        from django.conf import settings
        from django.db import connections

        default = settings.DATABASES["default"]
        test_name = (default.get("TEST") or {}).get("NAME") or f"test_{default['NAME']}"
        default["NAME"] = test_name
        # Drop any connection opened against the dev name so the new name takes.
        connections["default"].close()
        print(f"targeting test database: {test_name}")


def _orphan_nodegroups(models):
    """Nodegroups with no nodes and no tiles -- safe to delete.

    A deleted node can orphan its nodegroup, whose cards then break graph
    imports. One with no nodes may still own tiles (resource data) that deletion
    would cascade away, so any with tiles are reported but not offered."""
    orphans = []
    for ng in models.NodeGroup.objects.all():
        if models.Node.objects.filter(nodegroup_id=ng.nodegroupid).exists():
            continue
        tile_count = models.TileModel.objects.filter(
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
    for path in glob.glob(os.path.join(GRAPHS_DIR, "**", "*.json"), recursive=True):
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


def _write_alias_class(alias_file, classname, nodes):
    alias_file.write(f"class {classname}(AbstractAliases):\n")
    for node in nodes:
        alias_file.write(f'    {node.alias.upper()} = "{node.alias}"\n')
    alias_file.write(
        f"\n    @staticmethod\n"
        f"    def get_aliases():\n"
        f"        return AbstractAliases.get_dict({classname})\n"
    )


def _create_alias_file(models, slug, json_aliases):
    nodes = (
        models.Node.objects.filter(graph__slug=slug)
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

    filename = os.path.join(ALIAS_DIR, slug + ".py")
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


def _print_drift_fix(drift_nodes, orphan_nodegroups, settings_module):
    """Print a self-contained snippet that deletes the drift nodes and orphan
    nodegroups (with their dangling cards). Review before running."""
    if not drift_nodes and not orphan_nodegroups:
        return
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


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--target",
        choices=["dev", "test"],
        default="dev",
        help="Which database to read: the local dev DB or the test DB (default: dev)",
    )
    parser.add_argument(
        "--settings",
        default=os.environ.get("DJANGO_SETTINGS_MODULE", "bcap.settings"),
        help="Django settings module (default: bcap.settings)",
    )
    args = parser.parse_args()
    _bootstrap_django(args.settings, args.target)

    from arches.app.models import models

    orphan_nodegroups = _orphan_nodegroups(models)

    # Only regenerate alias files that already exist.
    existing = sorted(
        f[:-3]
        for f in os.listdir(ALIAS_DIR)
        if f.endswith(".py") and f != "__init__.py"
    )
    slugs_present = set(
        models.Graph.objects.filter(slug__in=existing).values_list("slug", flat=True)
    )
    json_aliases = _json_aliases_by_slug()
    all_drift = []
    for slug in existing:
        if slug in slugs_present:
            drift_nodes = _create_alias_file(models, slug, json_aliases)
            all_drift.extend((slug, node) for node in drift_nodes)
        else:
            print(f"SKIP {slug}: no graph with that slug in the DB")
    _print_drift_fix(all_drift, orphan_nodegroups, args.settings)


if __name__ == "__main__":
    main()
