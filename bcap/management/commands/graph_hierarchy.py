"""
Management command: graph_hierarchy

Prints the node hierarchy of a resource model graph, showing each node's alias,
datatype, and whether its nodegroup is 1:1 or 1:m (cardinality).

Usage:
    manage.py graph_hierarchy <graph-slug>
    manage.py graph_hierarchy <graph-slug> --show-semantic

Output legend:
    [1]  node belongs to a 1:1 nodegroup (at most one tile per resource)
    [n]  node belongs to a 1:m nodegroup (multiple tiles allowed per resource)
    *    this node is the grouping (collector) node of its nodegroup
"""

from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError

from arches.app.models.models import Edge, GraphModel, Node


class Command(BaseCommand):
    help = "Print the node hierarchy of a resource model graph with cardinality annotations."

    def add_arguments(self, parser):
        parser.add_argument(
            "graph_slug",
            help="Slug of the graph to inspect (e.g. 'archaeological-site')",
        )
        parser.add_argument(
            "--show-semantic",
            action="store_true",
            default=False,
            help="Include semantic (non-data) nodes in the output (default: hidden)",
        )

    def handle(self, *args, **options):
        slug = options["graph_slug"]
        show_semantic = options["show_semantic"]

        try:
            graph = GraphModel.objects.filter(source_identifier__isnull=True).get(
                slug=slug
            )
        except GraphModel.DoesNotExist:
            raise CommandError(f"No graph found with slug '{slug}'")

        # Load all nodes for this graph in one query, with nodegroup data
        nodes_qs = Node.objects.filter(graph=graph).select_related("nodegroup")
        nodes_by_id = {str(node.nodeid): node for node in nodes_qs}

        # Load all edges for this graph in one query
        edges_qs = Edge.objects.filter(graph=graph).only("domainnode", "rangenode")

        # Build parent→[children] adjacency map
        children_of = defaultdict(list)
        for edge in edges_qs:
            children_of[str(edge.domainnode_id)].append(str(edge.rangenode_id))

        # Find the root node
        root = next(
            (n for n in nodes_by_id.values() if n.istopnode),
            None,
        )
        if root is None:
            raise CommandError(f"Graph '{slug}' has no top node.")

        self.stdout.write(
            self.style.SUCCESS(f"Graph: {graph.name}  (slug={graph.slug})\n")
        )
        self.stdout.write(
            "Legend:  [1] = 1:1 nodegroup  [n] = 1:m nodegroup  * = nodegroup header\n"
        )
        self.stdout.write("─" * 72 + "\n")

        self._print_node(
            node_id=str(root.nodeid),
            nodes_by_id=nodes_by_id,
            children_of=children_of,
            show_semantic=show_semantic,
            depth=0,
        )

    def _print_node(self, node_id, nodes_by_id, children_of, show_semantic, depth):
        node = nodes_by_id.get(node_id)
        if node is None:
            return

        is_semantic = node.datatype == "semantic"
        if is_semantic and not show_semantic:
            # Still recurse so we don't skip subtrees hidden under semantic nodes
            for child_id in sorted(
                children_of.get(node_id, []),
                key=lambda nid: (
                    nodes_by_id[nid].sortorder or 0 if nid in nodes_by_id else 0
                ),
            ):
                self._print_node(
                    child_id, nodes_by_id, children_of, show_semantic, depth
                )
            return

        nodegroup = node.nodegroup
        is_collector = (
            str(node.nodeid) == str(node.nodegroup_id) and node.nodegroup_id is not None
        )
        # Cardinality only means something at the nodegroup boundary (collector node).
        # Non-collector nodes share a tile with their collector, so they are always
        # 1:1 within that tile regardless of the nodegroup's overall cardinality.
        if not nodegroup:
            card_label = "   "
        elif is_collector:
            card_label = f"[{nodegroup.cardinality}]"
        else:
            card_label = "[1]"
        collector_marker = "*" if is_collector else " "

        indent = "    " * depth
        alias_display = node.alias or f"(no alias: {node.nodeid})"
        datatype_display = f"  <{node.datatype}>" if not is_semantic else ""

        line = f"{indent}{collector_marker} {card_label}  {alias_display}{datatype_display}"
        self.stdout.write(line)

        for child_id in sorted(
            children_of.get(node_id, []),
            key=lambda nid: (
                nodes_by_id[nid].sortorder or 0 if nid in nodes_by_id else 0
            ),
        ):
            self._print_node(
                child_id, nodes_by_id, children_of, show_semantic, depth + 1
            )
