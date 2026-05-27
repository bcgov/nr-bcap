#!/usr/bin/env python
"""Regenerate the node-alias files in bcap/util/aliases from the database.

For each graph that already has an alias file, writes one
``<GraphSlug>Aliases`` class with an ``ALIAS = "alias"`` constant per
non-semantic node. Only existing files are regenerated; new graphs are not
added automatically.

Runs standalone (it bootstraps Django itself). Target either the local dev
database or the runner-created test database (test_<name>, e.g. with --keepdb):

    python3 tools/regen_aliases.py                 # dev DB (default)
    python3 tools/regen_aliases.py --target test   # test_<name> DB

Idea given from: Brett Ferguson
"""

import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIAS_DIR = os.path.join(REPO_ROOT, "bcap", "util", "aliases")


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


# Words whose camel-case form isn't just .title() (acronyms in class names).
_ACRONYMS = {"hca": "HCA"}


def _snake_to_camel(snake_str):
    return "".join(_ACRONYMS.get(word, word.title()) for word in snake_str.split("_"))


def _create_alias_file(models, slug):
    nodes = (
        models.Node.objects.exclude(datatype__in=["semantic"])
        .filter(graph__slug=slug)
        .prefetch_related("graph")
        .order_by("graph__slug", "alias")
        .all()
    )
    filename = os.path.join(ALIAS_DIR, slug + ".py")
    classname = _snake_to_camel(slug) + "Aliases"
    print(slug, "->", filename, f"({len(nodes)} nodes)")
    with open(filename, "w") as alias_file:
        alias_file.write("from bcap.util.bcap_aliases import AbstractAliases\n\n\n")
        alias_file.write(f"class {classname}(AbstractAliases):\n")
        for node in nodes:
            alias_file.write(f'    {node.alias.upper()} = "{node.alias}"\n')
        alias_file.write(
            f"\n    @staticmethod\n"
            f"    def get_aliases():\n"
            f"        return AbstractAliases.get_dict({classname})\n"
        )


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

    # Only regenerate alias files that already exist.
    existing = sorted(
        f[:-3]
        for f in os.listdir(ALIAS_DIR)
        if f.endswith(".py") and f != "__init__.py"
    )
    slugs_present = set(
        models.Graph.objects.filter(slug__in=existing).values_list("slug", flat=True)
    )
    for slug in existing:
        if slug in slugs_present:
            _create_alias_file(models, slug)
        else:
            print(f"SKIP {slug}: no graph with that slug in the DB")


if __name__ == "__main__":
    main()
