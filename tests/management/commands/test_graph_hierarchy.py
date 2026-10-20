from io import StringIO
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

_MODULE = "bcap.management.commands.graph_hierarchy"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid():
    return str(uuid4())


def _make_node(
    nodeid,
    alias,
    datatype="string",
    nodegroup_id=None,
    sortorder=0,
    istopnode=False,
    cardinality="1",
):
    node = MagicMock()
    node.nodeid = nodeid
    node.alias = alias
    node.datatype = datatype
    # Default: node is its own nodegroup collector
    node.nodegroup_id = nodegroup_id if nodegroup_id is not None else nodeid
    node.sortorder = sortorder
    node.istopnode = istopnode
    ng = MagicMock()
    ng.cardinality = cardinality
    node.nodegroup = ng
    return node


def _make_edge(domain_id, range_id):
    edge = MagicMock()
    edge.domainnode_id = domain_id
    edge.rangenode_id = range_id
    return edge


class _GraphNotFound(Exception):
    pass


def _run(slug, *, show_semantic=False, graph_obj=None, nodes=(), edges=()):
    """Execute graph_hierarchy with mocked DB; returns (stdout, stderr)."""
    out, err = StringIO(), StringIO()
    kwargs = {"stdout": out, "stderr": err, "no_color": True}
    if show_semantic:
        kwargs["show_semantic"] = True

    with (
        patch(f"{_MODULE}.GraphModel") as mock_gm,
        patch(f"{_MODULE}.Node") as mock_node_cls,
        patch(f"{_MODULE}.Edge") as mock_edge_cls,
    ):
        mock_gm.DoesNotExist = _GraphNotFound
        if graph_obj is None:
            mock_gm.objects.filter.return_value.get.side_effect = _GraphNotFound
        else:
            mock_gm.objects.filter.return_value.get.return_value = graph_obj

        mock_node_cls.objects.filter.return_value.select_related.return_value = list(
            nodes
        )
        mock_edge_cls.objects.filter.return_value.only.return_value = list(edges)

        call_command("graph_hierarchy", slug, **kwargs)

    return out.getvalue(), err.getvalue()


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestGraphHierarchyErrors(SimpleTestCase):

    def test_missing_graph_raises_command_error(self):
        with self.assertRaises(CommandError):
            _run("nonexistent-slug")

    def test_no_top_node_raises_command_error(self):
        graph = MagicMock()
        graph.name = "Test"
        graph.slug = "test"
        node = _make_node(_uuid(), "some_node", istopnode=False)
        with self.assertRaises(CommandError):
            _run("test", graph_obj=graph, nodes=[node])


# ---------------------------------------------------------------------------
# Output content
# ---------------------------------------------------------------------------


class TestGraphHierarchyOutput(SimpleTestCase):

    def setUp(self):
        self.graph = MagicMock()
        self.graph.name = "My Graph"
        self.graph.slug = "my-graph"
        self.root_id = _uuid()
        self.root = _make_node(self.root_id, "root_node", istopnode=True)

    def test_graph_name_in_output(self):
        out, _ = _run("my-graph", graph_obj=self.graph, nodes=[self.root])
        self.assertIn("My Graph", out)

    def test_graph_slug_in_output(self):
        out, _ = _run("my-graph", graph_obj=self.graph, nodes=[self.root])
        self.assertIn("my-graph", out)

    def test_legend_in_output(self):
        out, _ = _run("my-graph", graph_obj=self.graph, nodes=[self.root])
        self.assertIn("Legend", out)

    def test_root_alias_in_output(self):
        out, _ = _run("my-graph", graph_obj=self.graph, nodes=[self.root])
        self.assertIn("root_node", out)

    def test_datatype_shown_for_data_node(self):
        node = _make_node(self.root_id, "date_field", datatype="date", istopnode=True)
        out, _ = _run("my-graph", graph_obj=self.graph, nodes=[node])
        self.assertIn("<date>", out)

    def test_datatype_not_shown_for_semantic_node(self):
        sem_id = _uuid()
        sem = _make_node(sem_id, "the_semantic", datatype="semantic")
        out, _ = _run(
            "my-graph",
            show_semantic=True,
            graph_obj=self.graph,
            nodes=[self.root, sem],
            edges=[_make_edge(self.root_id, sem_id)],
        )
        sem_lines = [l for l in out.splitlines() if "the_semantic" in l]
        self.assertTrue(sem_lines)
        self.assertNotIn("<semantic>", sem_lines[0])


# ---------------------------------------------------------------------------
# Semantic node visibility
# ---------------------------------------------------------------------------


class TestSemanticNodes(SimpleTestCase):

    def setUp(self):
        self.graph = MagicMock()
        self.graph.name = "G"
        self.graph.slug = "g"
        self.root_id = _uuid()
        self.root = _make_node(self.root_id, "root_node", istopnode=True)

    def test_semantic_hidden_by_default(self):
        sem_id = _uuid()
        sem = _make_node(sem_id, "hidden_semantic", datatype="semantic")
        out, _ = _run(
            "g",
            graph_obj=self.graph,
            nodes=[self.root, sem],
            edges=[_make_edge(self.root_id, sem_id)],
        )
        self.assertNotIn("hidden_semantic", out)

    def test_semantic_shown_with_flag(self):
        sem_id = _uuid()
        sem = _make_node(sem_id, "visible_semantic", datatype="semantic")
        out, _ = _run(
            "g",
            show_semantic=True,
            graph_obj=self.graph,
            nodes=[self.root, sem],
            edges=[_make_edge(self.root_id, sem_id)],
        )
        self.assertIn("visible_semantic", out)

    def test_child_under_hidden_semantic_still_printed(self):
        """Non-semantic descendants of hidden semantic nodes must still appear."""
        sem_id = _uuid()
        child_id = _uuid()
        sem = _make_node(sem_id, "sem_wrapper", datatype="semantic")
        child = _make_node(child_id, "visible_child", datatype="string")
        out, _ = _run(
            "g",
            graph_obj=self.graph,
            nodes=[self.root, sem, child],
            edges=[_make_edge(self.root_id, sem_id), _make_edge(sem_id, child_id)],
        )
        self.assertIn("visible_child", out)
        self.assertNotIn("sem_wrapper", out)

    def test_child_under_hidden_semantic_uses_same_depth(self):
        """Children whose semantic parent is hidden should not gain extra indentation."""
        sem_id = _uuid()
        child_id = _uuid()
        sem = _make_node(sem_id, "sem_wrapper", datatype="semantic")
        child = _make_node(child_id, "direct_child", datatype="string")
        # direct child of root (no semantic) for comparison
        sibling_id = _uuid()
        sibling = _make_node(sibling_id, "sibling_child", datatype="string")
        out, _ = _run(
            "g",
            graph_obj=self.graph,
            nodes=[self.root, sem, child, sibling],
            edges=[
                _make_edge(self.root_id, sem_id),
                _make_edge(sem_id, child_id),
                _make_edge(self.root_id, sibling_id),
            ],
        )
        lines = out.splitlines()
        child_line = next(l for l in lines if "direct_child" in l)
        sibling_line = next(l for l in lines if "sibling_child" in l)
        # Both should have the same indentation depth since sem is hidden
        child_indent = len(child_line) - len(child_line.lstrip())
        sibling_indent = len(sibling_line) - len(sibling_line.lstrip())
        self.assertEqual(child_indent, sibling_indent)


# ---------------------------------------------------------------------------
# Collector markers and cardinality
# ---------------------------------------------------------------------------


class TestCardinality(SimpleTestCase):

    def setUp(self):
        self.graph = MagicMock()
        self.graph.name = "G"
        self.graph.slug = "g"

    def test_collector_node_marked_with_asterisk(self):
        root_id = _uuid()
        # nodegroup_id == nodeid → collector
        node = _make_node(
            root_id, "collector_node", nodegroup_id=root_id, istopnode=True
        )
        out, _ = _run("g", graph_obj=self.graph, nodes=[node])
        lines = [l for l in out.splitlines() if "collector_node" in l]
        self.assertTrue(lines)
        self.assertIn("*", lines[0])

    def test_non_collector_node_not_marked_with_asterisk(self):
        root_id = _uuid()
        child_id = _uuid()
        # Both share root's nodegroup; child is not the collector
        root = _make_node(root_id, "the_root", nodegroup_id=root_id, istopnode=True)
        child = _make_node(child_id, "child_field", nodegroup_id=root_id)
        out, _ = _run(
            "g",
            graph_obj=self.graph,
            nodes=[root, child],
            edges=[_make_edge(root_id, child_id)],
        )
        child_lines = [l for l in out.splitlines() if "child_field" in l]
        self.assertTrue(child_lines)
        self.assertNotIn("*", child_lines[0])

    def test_many_cardinality_label(self):
        root_id = _uuid()
        node = _make_node(root_id, "repeating", cardinality="n", istopnode=True)
        out, _ = _run("g", graph_obj=self.graph, nodes=[node])
        self.assertIn("[n]", out)

    def test_one_cardinality_label(self):
        root_id = _uuid()
        node = _make_node(root_id, "single", cardinality="1", istopnode=True)
        out, _ = _run("g", graph_obj=self.graph, nodes=[node])
        self.assertIn("[1]", out)

    def test_non_collector_always_shows_one_label(self):
        """Non-collector nodes show [1] regardless of their nodegroup cardinality."""
        root_id = _uuid()
        child_id = _uuid()
        # Nodegroup cardinality is n, but child is not the collector
        root = _make_node(
            root_id, "the_root", nodegroup_id=root_id, istopnode=True, cardinality="n"
        )
        child = _make_node(
            child_id, "child_field", nodegroup_id=root_id, cardinality="n"
        )
        out, _ = _run(
            "g",
            graph_obj=self.graph,
            nodes=[root, child],
            edges=[_make_edge(root_id, child_id)],
        )
        child_lines = [l for l in out.splitlines() if "child_field" in l]
        self.assertTrue(child_lines)
        self.assertIn("[1]", child_lines[0])


# ---------------------------------------------------------------------------
# Child ordering
# ---------------------------------------------------------------------------


class TestChildOrdering(SimpleTestCase):

    def setUp(self):
        self.graph = MagicMock()
        self.graph.name = "G"
        self.graph.slug = "g"

    def test_children_sorted_by_sortorder_ascending(self):
        root_id = _uuid()
        first_id = _uuid()
        second_id = _uuid()
        root = _make_node(root_id, "root_node", istopnode=True)
        first = _make_node(first_id, "aaa_first", sortorder=1)
        second = _make_node(second_id, "zzz_second", sortorder=2)
        out, _ = _run(
            "g",
            graph_obj=self.graph,
            nodes=[root, first, second],
            edges=[_make_edge(root_id, first_id), _make_edge(root_id, second_id)],
        )
        self.assertLess(out.index("aaa_first"), out.index("zzz_second"))

    def test_higher_sortorder_appears_later(self):
        root_id = _uuid()
        first_id = _uuid()
        second_id = _uuid()
        root = _make_node(root_id, "root_node", istopnode=True)
        # Lower sortorder → appears earlier
        first = _make_node(first_id, "zzz_lower_order", sortorder=1)
        second = _make_node(second_id, "aaa_higher_order", sortorder=10)
        out, _ = _run(
            "g",
            graph_obj=self.graph,
            nodes=[root, first, second],
            edges=[_make_edge(root_id, first_id), _make_edge(root_id, second_id)],
        )
        self.assertLess(out.index("zzz_lower_order"), out.index("aaa_higher_order"))

    def test_child_indented_more_than_parent(self):
        root_id = _uuid()
        child_id = _uuid()
        root = _make_node(root_id, "root_node", istopnode=True)
        child = _make_node(child_id, "child_node")
        out, _ = _run(
            "g",
            graph_obj=self.graph,
            nodes=[root, child],
            edges=[_make_edge(root_id, child_id)],
        )
        lines = out.splitlines()
        root_line = next(l for l in lines if "root_node" in l)
        child_line = next(l for l in lines if "child_node" in l)
        root_indent = len(root_line) - len(root_line.lstrip())
        child_indent = len(child_line) - len(child_line.lstrip())
        self.assertGreater(child_indent, root_indent)

    def test_grandchild_indented_more_than_child(self):
        root_id = _uuid()
        child_id = _uuid()
        grand_id = _uuid()
        root = _make_node(root_id, "root_node", istopnode=True)
        child = _make_node(child_id, "child_node")
        grand = _make_node(grand_id, "grand_node")
        out, _ = _run(
            "g",
            graph_obj=self.graph,
            nodes=[root, child, grand],
            edges=[_make_edge(root_id, child_id), _make_edge(child_id, grand_id)],
        )
        lines = out.splitlines()
        child_line = next(l for l in lines if "child_node" in l)
        grand_line = next(l for l in lines if "grand_node" in l)
        child_indent = len(child_line) - len(child_line.lstrip())
        grand_indent = len(grand_line) - len(grand_line.lstrip())
        self.assertGreater(grand_indent, child_indent)
