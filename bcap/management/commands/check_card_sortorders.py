"""
Management command: check_card_sortorders

Checks all package graph cards and nodes for NULL or duplicate sortorder
values within their sibling group.  Non-unique sortorders within the same
group produce non-deterministic field ordering in the generated API schema
because PostgreSQL falls back to physical row insertion order when values are
equal or absent — which differs between a fresh CI database (JSON file order)
and a local database built up over time.

Checks performed:
  - Cards: grouped by parentnodegroup_id — siblings must have unique sortorders.
  - Nodes: grouped by nodegroup_id — nodes within the same nodegroup must have
    unique sortorders.

By default the command reports problems and exits non-zero if any are found.
Pass --fix to assign explicit sortorder values and update both the package
JSON files and the live DB rows.

Fix strategy: for each group that contains any NULL or duplicate sortorders,
items are sorted by existing sortorder (NULLs last) and assigned fresh 0-based
sequential integers.  Items with unique sortorders keep their relative order.
Among duplicate-sortorder or NULL siblings the relative order is arbitrary
(Python stable sort preserves DB query order).

    python3 manage.py check_card_sortorders                          # check only (CI-safe)
    python3 manage.py check_card_sortorders --fix                    # fix JSON + DB
    python3 manage.py check_card_sortorders --resource-models-only   # skip branches
"""

import json
from collections import Counter
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from arches.app.models import models as arches_models


def _pkg():
    return Path(apps.get_app_config("bcap").path) / "pkg"


def _all_package_graphs():
    """Yield (doc, graphid, slug, path) for every graph JSON in the package."""
    for path in sorted((_pkg() / "graphs").rglob("*.json")):
        try:
            doc = json.loads(path.read_text())
            graph = doc["graph"][0]
            yield doc, graph["graphid"], graph["slug"], path
        except (KeyError, IndexError, ValueError):
            continue


def _has_problem(group):
    """True if the sibling group contains any NULL or duplicate sortorders."""
    sortorders = [c.sortorder for c in group]
    if any(s is None for s in sortorders):
        return True
    non_null = [s for s in sortorders if s is not None]
    return len(non_null) != len(set(non_null))


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Assign explicit sortorders and update the JSON files and DB.",
        )
        parser.add_argument(
            "--resource-models-only",
            action="store_true",
            help="Only check resource model graphs; skip branch graphs.",
        )

    def handle(self, *args, **options):
        fix = options["fix"]
        resource_models_only = options["resource_models_only"]
        problems = []

        for doc, graphid, slug, path in _all_package_graphs():
            if resource_models_only and not doc["graph"][0].get("isresource", False):
                continue
            # Build lookups for JSON file updates.
            json_cards_by_id = {}
            for json_card in doc["graph"][0].get("cards", []):
                cid = str(json_card.get("cardid", ""))
                if cid:
                    json_cards_by_id[cid] = json_card

            json_nodes_by_id = {}
            for json_node in doc["graph"][0].get("nodes", []):
                nid = str(json_node.get("nodeid", ""))
                if nid:
                    json_nodes_by_id[nid] = json_node

            # Group source cards by their parent nodegroup (None = top-level).
            all_cards = list(
                arches_models.CardModel.objects.filter(
                    graph_id=graphid,
                    source_identifier__isnull=True,
                ).select_related("nodegroup")
            )
            parent_groups: dict = {}
            for card in all_cards:
                key = card.nodegroup.parentnodegroup_id
                parent_groups.setdefault(key, []).append(card)

            graph_dirty = False
            for group in parent_groups.values():
                if not _has_problem(group):
                    continue

                counts = Counter(c.sortorder for c in group)
                # Print a group-level header followed by all siblings so the
                # user can see the full context needed for a manual fix.
                parent_key = group[0].nodegroup.parentnodegroup_id
                self.stdout.write(
                    self.style.WARNING(
                        f"  [{slug}] parent nodegroup: {parent_key}"
                    )
                )
                sorted_for_display = sorted(
                    group,
                    key=lambda c: (
                        c.sortorder is None,
                        c.sortorder if c.sortorder is not None else 999_999,
                    ),
                )
                for card in sorted_for_display:
                    so = card.sortorder
                    if so is None:
                        marker = "  [NULL]    "
                        problems.append((slug, card.cardid, str(card.name)))
                    elif counts[so] > 1:
                        marker = f"  [dup={so:>4}]"
                        problems.append((slug, card.cardid, str(card.name)))
                    else:
                        marker = f"  [ok ={so:>4}]"
                    self.stdout.write(
                        f"    {marker} {card.name} ({card.cardid})"
                    )

                if not fix:
                    continue

                # Sort by existing sortorder (NULLs last); duplicates and NULLs
                # keep their DB query order (stable sort).  Then assign fresh
                # 0-based sequential integers.
                sorted_group = sorted(
                    group,
                    key=lambda c: (
                        c.sortorder is None,
                        c.sortorder if c.sortorder is not None else 0,
                    ),
                )
                db_updates = []
                for new_so, card in enumerate(sorted_group):
                    if card.sortorder == new_so:
                        continue
                    self.stdout.write(
                        f"    {slug} / {card.name}: {card.sortorder} -> {new_so}"
                    )
                    card.sortorder = new_so
                    json_card = json_cards_by_id.get(str(card.cardid))
                    if json_card is not None:
                        json_card["sortorder"] = new_so
                        graph_dirty = True
                    db_updates.append(card)

                if db_updates:
                    with transaction.atomic():
                        arches_models.CardModel.objects.bulk_update(
                            db_updates, ["sortorder"]
                        )

            # --- nodes: check sortorder uniqueness within each nodegroup ---
            all_nodes = list(
                arches_models.Node.objects.filter(graph_id=graphid)
            )
            node_groups: dict = {}
            for node in all_nodes:
                # The grouping node (nodeid == nodegroup_id) is the card root —
                # its sortorder positions the card, not a field within the card.
                # Exclude it so it doesn't create false duplicate positives against
                # child nodes that legitimately start at sortorder 0.
                if str(node.nodeid) == str(node.nodegroup_id):
                    continue
                node_groups.setdefault(node.nodegroup_id, []).append(node)

            for group in node_groups.values():
                if not _has_problem(group):
                    continue

                counts = Counter(n.sortorder for n in group)
                self.stdout.write(
                    self.style.WARNING(
                        f"  [{slug}] nodegroup: {group[0].nodegroup_id}"
                    )
                )
                sorted_for_display = sorted(
                    group,
                    key=lambda n: (
                        n.sortorder is None,
                        n.sortorder if n.sortorder is not None else 999_999,
                    ),
                )
                for node in sorted_for_display:
                    so = node.sortorder
                    if so is None:
                        marker = "  [NULL]    "
                        problems.append((slug, node.nodeid, str(node.name)))
                    elif counts[so] > 1:
                        marker = f"  [dup={so:>4}]"
                        problems.append((slug, node.nodeid, str(node.name)))
                    else:
                        marker = f"  [ok ={so:>4}]"
                    self.stdout.write(
                        f"    {marker} {node.name} ({node.nodeid})"
                    )

                if not fix:
                    continue

                sorted_group = sorted(
                    group,
                    key=lambda n: (
                        n.sortorder is None,
                        n.sortorder if n.sortorder is not None else 0,
                    ),
                )
                db_updates = []
                for new_so, node in enumerate(sorted_group):
                    if node.sortorder == new_so:
                        continue
                    self.stdout.write(
                        f"    {slug} / {node.name}: {node.sortorder} -> {new_so}"
                    )
                    node.sortorder = new_so
                    json_node = json_nodes_by_id.get(str(node.nodeid))
                    if json_node is not None:
                        json_node["sortorder"] = new_so
                        graph_dirty = True
                    db_updates.append(node)

                if db_updates:
                    with transaction.atomic():
                        arches_models.Node.objects.bulk_update(
                            db_updates, ["sortorder"]
                        )

            if graph_dirty:
                path.write_text(
                    json.dumps(doc, indent=4, ensure_ascii=False) + "\n"
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  updated: {path.relative_to(_pkg().parent)}"
                    )
                )

        if not problems:
            self.stdout.write(
                self.style.SUCCESS(
                    "All package graph cards and nodes have explicit, unique "
                    "sortorders within their sibling groups."
                )
            )
        elif fix:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n{len(problems)} item(s) updated. Commit the JSON changes."
                )
            )
        else:
            self.stdout.write("")
            self.stdout.write(
                self.style.ERROR(
                    f"{len(problems)} item(s) with NULL or duplicate sortorder. "
                    "Run with --fix to assign explicit sortorders."
                )
            )
            raise SystemExit(1)
