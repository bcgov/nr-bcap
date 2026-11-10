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
  - Nodes: grouped by direct parent node (via Edge table) — siblings under the
    same parent node must have unique sortorders.

By default the command reports problems and exits non-zero if any are found.

Fix flags (update JSON files and live DB rows):
  --fix-cards       Resolve NULL/duplicate card sortorders.
  --fix-nodes       Resolve NULL/duplicate node sortorders.
  --fix             Shorthand for --fix-cards --fix-nodes.
  --align-nodes     Within each parent-node sibling group, nodes with widgets
                    are ordered first by widget position; semantic nodes without
                    widgets are appended after, by existing sortorder.  Always
                    produces unique sortorders — no need to combine with --fix-nodes.

Fix strategy for --fix-cards / --fix-nodes: items are sorted by existing
sortorder (NULLs last) and assigned fresh 0-based sequential integers.  Items
with unique sortorders keep their relative order; duplicates and NULLs keep
their DB query order (Python stable sort).

    python3 manage.py check_card_sortorders                            # check only (CI-safe)
    python3 manage.py check_card_sortorders --fix                      # fix cards + nodes
    python3 manage.py check_card_sortorders --fix-cards                # fix cards only
    python3 manage.py check_card_sortorders --fix-nodes                # fix nodes only
    python3 manage.py check_card_sortorders --align-nodes              # align nodes to widget order
    python3 manage.py check_card_sortorders --fix-nodes --align-nodes  # fix non-widget nodes, align widget nodes
    python3 manage.py check_card_sortorders --resource-models-only     # skip branch graphs
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
            help="Shorthand for --fix-cards --fix-nodes.",
        )
        parser.add_argument(
            "--fix-cards",
            action="store_true",
            help="Resolve NULL/duplicate card sortorders within each parent nodegroup.",
        )
        parser.add_argument(
            "--fix-nodes",
            action="store_true",
            help="Resolve NULL/duplicate node sortorders within each nodegroup.",
        )
        parser.add_argument(
            "--align-nodes",
            action="store_true",
            help=(
                "Within each parent-node sibling group, nodes with widgets are "
                "ordered first by CardXNodeXWidget.sortorder; nodes without "
                "widgets (semantic nodes) follow, ordered by existing sortorder. "
                "Always produces unique sortorders within every sibling group."
            ),
        )
        parser.add_argument(
            "--resource-models-only",
            action="store_true",
            help="Only check resource model graphs; skip branch graphs.",
        )

    def handle(self, *args, **options):
        fix = options["fix"]
        fix_cards = options["fix_cards"] or fix
        fix_nodes = options["fix_nodes"] or fix
        align_nodes = options["align_nodes"]
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

                if not fix_cards:
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

            # Build node sibling groups (needed by both align-nodes and the
            # node check below).  Nodes are only comparable with their direct
            # tree siblings, so we group via the Edge table rather than by
            # nodegroup_id.
            all_nodes = list(
                arches_models.Node.objects.filter(graph_id=graphid)
            )
            nodes_by_id = {str(n.nodeid): n for n in all_nodes}

            edges = arches_models.Edge.objects.filter(
                graph_id=graphid
            ).values_list("rangenode_id", "domainnode_id")

            node_sibling_groups: dict = {}
            for child_id, parent_id in edges:
                child = nodes_by_id.get(str(child_id))
                if child is not None:
                    node_sibling_groups.setdefault(str(parent_id), []).append(child)

            # --- align-nodes: validate widget sortorders, then align ---
            # Execution order:
            #   1. Pre-check: every card's widgets must have unique sortorders.
            #      Abort alignment for this graph if any card fails.
            #   2. Align: within each parent-node sibling group, widget nodes
            #      come first (sorted by widget position), semantic nodes after
            #      (sorted by existing sortorder).
            # The node check below runs afterwards so reported state reflects
            # the aligned values.
            if align_nodes:
                widget_groups: dict = {}
                for w in arches_models.CardXNodeXWidget.objects.filter(
                    card__graph_id=graphid,
                    card__source_identifier__isnull=True,
                ).select_related("node", "card"):
                    widget_groups.setdefault(str(w.card_id), []).append(w)

                widget_invalid = False
                for widgets in widget_groups.values():
                    if not _has_problem(widgets):
                        continue
                    widget_invalid = True
                    card_name = widgets[0].card.name
                    counts = Counter(w.sortorder for w in widgets)
                    self.stdout.write(
                        self.style.ERROR(
                            f"  [{slug}] --align-nodes blocked: "
                            f"card '{card_name}' has NULL/duplicate widget sortorders"
                        )
                    )
                    sorted_w = sorted(
                        widgets,
                        key=lambda w: (
                            w.sortorder is None,
                            w.sortorder if w.sortorder is not None else 999_999,
                        ),
                    )
                    for w in sorted_w:
                        so = w.sortorder
                        if so is None:
                            marker = "  [NULL]    "
                            problems.append((slug, w.node_id, str(w.node.name)))
                        elif counts[so] > 1:
                            marker = f"  [dup={so:>4}]"
                            problems.append((slug, w.node_id, str(w.node.name)))
                        else:
                            marker = f"  [ok ={so:>4}]"
                        self.stdout.write(
                            f"    {marker} {w.node.name} ({w.node_id})"
                        )

                if not widget_invalid:
                    # Build node_id → widget sortorder lookup.
                    widget_so_by_node: dict = {}
                    for node_id, ws in arches_models.CardXNodeXWidget.objects.filter(
                        card__graph_id=graphid,
                        card__source_identifier__isnull=True,
                    ).values_list("node_id", "sortorder"):
                        nid = str(node_id)
                        if nid not in widget_so_by_node or (
                            ws is not None
                            and (
                                widget_so_by_node[nid] is None
                                or ws < widget_so_by_node[nid]
                            )
                        ):
                            widget_so_by_node[nid] = ws

                    for group in node_sibling_groups.values():
                        widget_nodes = sorted(
                            [n for n in group if str(n.nodeid) in widget_so_by_node],
                            key=lambda n: (
                                widget_so_by_node[str(n.nodeid)] is None,
                                widget_so_by_node[str(n.nodeid)]
                                if widget_so_by_node[str(n.nodeid)] is not None
                                else 0,
                            ),
                        )
                        non_widget_nodes = sorted(
                            [n for n in group if str(n.nodeid) not in widget_so_by_node],
                            key=lambda n: (
                                n.sortorder is None,
                                n.sortorder if n.sortorder is not None else 0,
                            ),
                        )
                        ordered = widget_nodes + non_widget_nodes

                        db_node_updates = []
                        for new_so, node in enumerate(ordered):
                            if node.sortorder == new_so:
                                continue
                            kind = (
                                "aligned to widget"
                                if str(node.nodeid) in widget_so_by_node
                                else "no widget, appended"
                            )
                            self.stdout.write(
                                f"    {slug} / {node.name}: "
                                f"{node.sortorder} -> {new_so} ({kind})"
                            )
                            node.sortorder = new_so
                            json_node = json_nodes_by_id.get(str(node.nodeid))
                            if json_node is not None:
                                json_node["sortorder"] = new_so
                                graph_dirty = True
                            db_node_updates.append(node)

                        if db_node_updates:
                            with transaction.atomic():
                                arches_models.Node.objects.bulk_update(
                                    db_node_updates, ["sortorder"]
                                )

            # --- nodes: check sortorder uniqueness within each parent-node group ---
            # Runs after --align-nodes so reported state reflects aligned values.
            for parent_id, group in node_sibling_groups.items():
                if not _has_problem(group):
                    continue

                parent_node = nodes_by_id.get(parent_id)
                parent_label = (
                    f"{parent_node.name} ({parent_id})"
                    if parent_node
                    else parent_id
                )
                counts = Counter(n.sortorder for n in group)
                self.stdout.write(
                    self.style.WARNING(
                        f"  [{slug}] parent node: {parent_label}"
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

                if not fix_nodes:
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
        elif fix_cards or fix_nodes or align_nodes:
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
