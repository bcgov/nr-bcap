"""Tests for the check_card_sortorders management command."""

import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.core.management import call_command
from django.test import SimpleTestCase

_MODULE = "bcap.management.commands.check_card_sortorders"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _uuid():
    return str(uuid4())


def _make_card(cardid=None, sortorder=None, name="Card A", parent_ng_id=None):
    card = MagicMock()
    card.cardid = cardid or _uuid()
    card.sortorder = sortorder
    card.name = name
    ng = MagicMock()
    ng.parentnodegroup_id = parent_ng_id
    card.nodegroup = ng
    return card


def _make_widget(
    node_id=None,
    card_id=None,
    sortorder=None,
    node_name="Field A",
    card_name="Card A",
    widget_id=None,
):
    w = MagicMock()
    w.id = widget_id or _uuid()
    w.node_id = node_id or _uuid()
    w.card_id = card_id or _uuid()
    w.sortorder = sortorder
    node = MagicMock()
    node.name = node_name
    w.node = node
    card_mock = MagicMock()
    card_mock.name = card_name
    w.card = card_mock
    return w


def _make_node(nodeid=None, sortorder=None, name="Node A"):
    node = MagicMock()
    node.nodeid = nodeid or _uuid()
    node.sortorder = sortorder
    node.name = name
    return node


def _make_path(relative="bcap/pkg/graphs/resource_models/Test.json"):
    p = MagicMock(spec=Path)
    p.is_relative_to.return_value = True
    p.relative_to.return_value = Path(relative)
    return p


def _make_doc(graphid, slug="test-graph", cards=(), nodes=(), widgets=()):
    return {
        "graph": [
            {
                "graphid": graphid,
                "slug": slug,
                "isresource": True,
                "cards": list(cards),
                "nodes": list(nodes),
                "cards_x_nodes_x_widgets": list(widgets),
            }
        ]
    }


def _run(
    *,
    fix=False,
    fix_cards=False,
    fix_nodes=False,
    align_nodes=False,
    resource_models_only=False,
    graphid=None,
    slug="test-graph",
    path=None,
    doc=None,
    cards=(),
    widgets=(),
    nodes=(),
    edges=(),
    widget_so=(),
):
    """
    Run check_card_sortorders with fully mocked dependencies.

    Returns (stdout, stderr, exit_code).  exit_code is 0 unless a SystemExit
    was raised, in which case it is the exit status.
    """
    gid = graphid or _uuid()
    if doc is None:
        doc = _make_doc(gid, slug=slug)
    if path is None:
        path = _make_path()

    out, err = StringIO(), StringIO()
    kwargs = {
        "stdout": out,
        "stderr": err,
        "no_color": True,
        "fix": fix,
        "fix_cards": fix_cards,
        "fix_nodes": fix_nodes,
        "align_nodes": align_nodes,
        "resource_models_only": resource_models_only,
    }

    def _fake_graphs(resource_models_only=False):
        yield doc, gid, slug, path

    # Minimal context-manager stub for transaction.atomic()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=None)
    cm.__exit__ = MagicMock(return_value=False)

    exit_code = 0
    with (
        patch(f"{_MODULE}._all_package_graphs", side_effect=_fake_graphs),
        patch(f"{_MODULE}.arches_models") as mock_m,
        patch(f"{_MODULE}.transaction") as mock_tx,
        patch(f"{_MODULE}.settings") as mock_settings,
    ):
        mock_settings.APP_ROOT = "/fake/app"
        mock_tx.atomic.return_value = cm

        # CardModel ORM chain: .filter(...).select_related(...)
        card_qs = MagicMock()
        card_qs.select_related.return_value = list(cards)
        mock_m.CardModel.objects.filter.return_value = card_qs

        # CardXNodeXWidget ORM chain: .filter(...).select_related(...) and
        # .filter(...).values_list("node_id", "sortorder")
        widget_qs = MagicMock()
        widget_qs.select_related.return_value = list(widgets)
        widget_qs.values_list.return_value = list(widget_so)
        mock_m.CardXNodeXWidget.objects.filter.return_value = widget_qs

        # Node.objects.filter(...) → list()
        mock_m.Node.objects.filter.return_value = list(nodes)

        # Edge ORM chain: .filter(...).values_list(...)
        edge_qs = MagicMock()
        edge_qs.values_list.return_value = list(edges)
        mock_m.Edge.objects.filter.return_value = edge_qs

        try:
            call_command("check_card_sortorders", **kwargs)
        except SystemExit as e:
            exit_code = e.code

    return out.getvalue(), err.getvalue(), exit_code


# ---------------------------------------------------------------------------
# _has_problem
# ---------------------------------------------------------------------------


class TestHasProblem(SimpleTestCase):
    """Unit tests for the _has_problem helper."""

    def _call(self, sortorders):
        from bcap.management.commands.check_card_sortorders import _has_problem

        items = [MagicMock(sortorder=s) for s in sortorders]
        return _has_problem(items)

    def test_empty_group_is_clean(self):
        self.assertFalse(self._call([]))

    def test_single_unique_sortorder_is_clean(self):
        self.assertFalse(self._call([0]))

    def test_multiple_unique_sortorders_are_clean(self):
        self.assertFalse(self._call([0, 1, 2]))

    def test_non_zero_start_is_clean(self):
        self.assertFalse(self._call([5, 10, 15]))

    def test_null_sortorder_is_problem(self):
        self.assertTrue(self._call([None]))

    def test_null_among_valid_sortorders_is_problem(self):
        self.assertTrue(self._call([0, None, 2]))

    def test_all_null_sortorders_is_problem(self):
        self.assertTrue(self._call([None, None]))

    def test_duplicate_sortorder_is_problem(self):
        self.assertTrue(self._call([0, 0]))

    def test_duplicate_among_valid_sortorders_is_problem(self):
        self.assertTrue(self._call([0, 1, 1, 2]))

    def test_all_zero_is_problem(self):
        self.assertTrue(self._call([0, 0, 0]))


# ---------------------------------------------------------------------------
# _all_package_graphs
# ---------------------------------------------------------------------------


class TestAllPackageGraphs(SimpleTestCase):
    """Unit tests for the filesystem-scanning generator."""

    def _graph_json(self, graphid, slug):
        return json.dumps({"graph": [{"graphid": graphid, "slug": slug}]})

    def _write_graph(self, directory, filename, graphid, slug):
        path = Path(directory) / filename
        path.write_text(self._graph_json(graphid, slug))
        return path

    def test_scans_resource_models_directory(self):
        from bcap.management.commands.check_card_sortorders import _all_package_graphs

        with tempfile.TemporaryDirectory() as tmp:
            rm_dir = Path(tmp) / "pkg" / "graphs" / "resource_models"
            rm_dir.mkdir(parents=True)
            gid = _uuid()
            self._write_graph(rm_dir, "RM.json", gid, "rm-graph")

            with patch(f"{_MODULE}.settings") as ms:
                ms.APP_ROOT = tmp
                results = list(_all_package_graphs())

        self.assertEqual(len(results), 1)
        _, _, slug, _ = results[0]
        self.assertEqual(slug, "rm-graph")

    def test_scans_branches_directory_by_default(self):
        from bcap.management.commands.check_card_sortorders import _all_package_graphs

        with tempfile.TemporaryDirectory() as tmp:
            br_dir = Path(tmp) / "pkg" / "graphs" / "branches"
            br_dir.mkdir(parents=True)
            self._write_graph(br_dir, "BR.json", _uuid(), "br-graph")

            with patch(f"{_MODULE}.settings") as ms:
                ms.APP_ROOT = tmp
                results = list(_all_package_graphs())

        slugs = {slug for _, _, slug, _ in results}
        self.assertIn("br-graph", slugs)

    def test_resource_models_only_skips_branches(self):
        from bcap.management.commands.check_card_sortorders import _all_package_graphs

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "pkg" / "graphs" / "resource_models").mkdir(parents=True)
            (Path(tmp) / "pkg" / "graphs" / "branches").mkdir(parents=True)
            self._write_graph(
                Path(tmp) / "pkg" / "graphs" / "resource_models",
                "RM.json",
                _uuid(),
                "rm-graph",
            )
            self._write_graph(
                Path(tmp) / "pkg" / "graphs" / "branches",
                "BR.json",
                _uuid(),
                "br-graph",
            )

            with patch(f"{_MODULE}.settings") as ms:
                ms.APP_ROOT = tmp
                results = list(_all_package_graphs(resource_models_only=True))

        slugs = {slug for _, _, slug, _ in results}
        self.assertIn("rm-graph", slugs)
        self.assertNotIn("br-graph", slugs)

    def test_invalid_json_is_skipped(self):
        from bcap.management.commands.check_card_sortorders import _all_package_graphs

        with tempfile.TemporaryDirectory() as tmp:
            rm_dir = Path(tmp) / "pkg" / "graphs" / "resource_models"
            rm_dir.mkdir(parents=True)
            (rm_dir / "bad.json").write_text("{not valid json")

            with patch(f"{_MODULE}.settings") as ms:
                ms.APP_ROOT = tmp
                results = list(_all_package_graphs())

        self.assertEqual(results, [])

    def test_missing_graph_key_is_skipped(self):
        from bcap.management.commands.check_card_sortorders import _all_package_graphs

        with tempfile.TemporaryDirectory() as tmp:
            rm_dir = Path(tmp) / "pkg" / "graphs" / "resource_models"
            rm_dir.mkdir(parents=True)
            (rm_dir / "no-graph.json").write_text(json.dumps({"other": "data"}))

            with patch(f"{_MODULE}.settings") as ms:
                ms.APP_ROOT = tmp
                results = list(_all_package_graphs())

        self.assertEqual(results, [])

    def test_missing_subdir_does_not_raise(self):
        from bcap.management.commands.check_card_sortorders import _all_package_graphs

        with tempfile.TemporaryDirectory() as tmp:
            # pkg/graphs exists but has no resource_models or branches subdirs
            (Path(tmp) / "pkg" / "graphs").mkdir(parents=True)

            with patch(f"{_MODULE}.settings") as ms:
                ms.APP_ROOT = tmp
                results = list(_all_package_graphs())

        self.assertEqual(results, [])


# ---------------------------------------------------------------------------
# Command — no problems
# ---------------------------------------------------------------------------


class TestCommandClean(SimpleTestCase):

    def test_clean_graph_prints_success_message(self):
        parent_id = _uuid()
        c1 = _make_card(sortorder=0, parent_ng_id=parent_id)
        c2 = _make_card(sortorder=1, parent_ng_id=parent_id)
        out, _, code = _run(cards=[c1, c2])
        self.assertIn("All", out)
        self.assertEqual(code, 0)

    def test_no_graphs_prints_success_message(self):
        out_io, err_io = StringIO(), StringIO()

        def _empty(resource_models_only=False):
            return iter([])

        with (
            patch(f"{_MODULE}._all_package_graphs", side_effect=_empty),
            patch(f"{_MODULE}.settings") as ms,
        ):
            ms.APP_ROOT = "/fake"
            call_command(
                "check_card_sortorders",
                stdout=out_io,
                stderr=err_io,
                no_color=True,
            )

        self.assertIn("All", out_io.getvalue())


# ---------------------------------------------------------------------------
# Command — check only (no fix flags): problems cause non-zero exit
# ---------------------------------------------------------------------------


class TestCommandCheckOnly(SimpleTestCase):

    def test_duplicate_card_sortorder_exits_nonzero(self):
        parent_id = _uuid()
        c1 = _make_card(sortorder=0, parent_ng_id=parent_id)
        c2 = _make_card(sortorder=0, parent_ng_id=parent_id)
        _, _, code = _run(cards=[c1, c2])
        self.assertEqual(code, 1)

    def test_null_card_sortorder_exits_nonzero(self):
        parent_id = _uuid()
        c = _make_card(sortorder=None, parent_ng_id=parent_id)
        _, _, code = _run(cards=[c])
        self.assertEqual(code, 1)

    def test_card_problem_names_appear_in_output(self):
        parent_id = _uuid()
        c1 = _make_card(sortorder=0, name="Card X", parent_ng_id=parent_id)
        c2 = _make_card(sortorder=0, name="Card Y", parent_ng_id=parent_id)
        out, _, _ = _run(cards=[c1, c2])
        self.assertIn("Card X", out)
        self.assertIn("Card Y", out)

    def test_duplicate_widget_sortorder_exits_nonzero(self):
        card_id = _uuid()
        w1 = _make_widget(card_id=card_id, sortorder=0)
        w2 = _make_widget(card_id=card_id, sortorder=0)
        _, _, code = _run(widgets=[w1, w2])
        self.assertEqual(code, 1)

    def test_null_widget_sortorder_exits_nonzero(self):
        card_id = _uuid()
        w = _make_widget(card_id=card_id, sortorder=None)
        _, _, code = _run(widgets=[w])
        self.assertEqual(code, 1)

    def test_duplicate_node_sortorder_exits_nonzero(self):
        parent_id = _uuid()
        child1_id = _uuid()
        child2_id = _uuid()
        n_parent = _make_node(nodeid=parent_id, sortorder=0)
        n1 = _make_node(nodeid=child1_id, sortorder=0)
        n2 = _make_node(nodeid=child2_id, sortorder=0)
        edges = [(child1_id, parent_id), (child2_id, parent_id)]
        _, _, code = _run(nodes=[n_parent, n1, n2], edges=edges)
        self.assertEqual(code, 1)

    def test_null_node_sortorder_exits_nonzero(self):
        parent_id = _uuid()
        child_id = _uuid()
        n_parent = _make_node(nodeid=parent_id, sortorder=0)
        n_child = _make_node(nodeid=child_id, sortorder=None)
        edges = [(child_id, parent_id)]
        _, _, code = _run(nodes=[n_parent, n_child], edges=edges)
        self.assertEqual(code, 1)

    def test_error_output_mentions_fix_flag(self):
        parent_id = _uuid()
        c = _make_card(sortorder=None, parent_ng_id=parent_id)
        out, _, _ = _run(cards=[c])
        self.assertIn("--fix", out)

    def test_slug_appears_in_problem_header(self):
        parent_id = _uuid()
        c = _make_card(sortorder=None, parent_ng_id=parent_id)
        out, _, _ = _run(cards=[c], slug="my-resource-model")
        self.assertIn("my-resource-model", out)


# ---------------------------------------------------------------------------
# Command — --fix-cards
# ---------------------------------------------------------------------------


class TestCommandFixCards(SimpleTestCase):

    def test_fix_cards_resolves_duplicate_card_sortorders_exit_zero(self):
        parent_id = _uuid()
        c1 = _make_card(sortorder=0, parent_ng_id=parent_id)
        c2 = _make_card(sortorder=0, parent_ng_id=parent_id)
        _, _, code = _run(fix_cards=True, cards=[c1, c2])
        self.assertEqual(code, 0)

    def test_fix_cards_prints_updated_summary(self):
        parent_id = _uuid()
        c1 = _make_card(sortorder=0, parent_ng_id=parent_id)
        c2 = _make_card(sortorder=0, parent_ng_id=parent_id)
        out, _, _ = _run(fix_cards=True, cards=[c1, c2])
        self.assertIn("updated", out.lower())

    def test_fix_cards_assigns_unique_sortorders_to_mocks(self):
        # Verify the in-memory card objects are updated with unique values.
        parent_id = _uuid()
        c1 = _make_card(sortorder=0, parent_ng_id=parent_id)
        c2 = _make_card(sortorder=0, parent_ng_id=parent_id)
        _run(fix_cards=True, cards=[c1, c2])
        self.assertNotEqual(c1.sortorder, c2.sortorder)

    def test_fix_cards_resolves_null_widget_sortorder(self):
        card_id = _uuid()
        w1 = _make_widget(card_id=card_id, sortorder=0)
        w2 = _make_widget(card_id=card_id, sortorder=None)
        _, _, code = _run(fix_cards=True, widgets=[w1, w2])
        self.assertEqual(code, 0)

    def test_fix_cards_assigns_unique_widget_sortorders(self):
        card_id = _uuid()
        w1 = _make_widget(card_id=card_id, sortorder=0)
        w2 = _make_widget(card_id=card_id, sortorder=0)
        _run(fix_cards=True, widgets=[w1, w2])
        self.assertNotEqual(w1.sortorder, w2.sortorder)

    def test_fix_flag_implies_fix_cards(self):
        # --fix is shorthand for --fix-cards --fix-nodes; cards should be fixed.
        parent_id = _uuid()
        c1 = _make_card(sortorder=0, parent_ng_id=parent_id)
        c2 = _make_card(sortorder=0, parent_ng_id=parent_id)
        _, _, code = _run(fix=True, cards=[c1, c2])
        self.assertEqual(code, 0)

    def test_fix_cards_writes_updated_file_when_json_matches(self):
        # When the doc contains JSON entries for both duplicate cards, the card
        # whose sortorder actually changes (new_so != old_so) will set
        # graph_dirty=True and trigger a file write.
        parent_id = _uuid()
        c1_id = _uuid()
        c2_id = _uuid()
        # Both cards are in the doc so the second one (new_so=1) finds its entry.
        doc = _make_doc(
            _uuid(),
            cards=[
                {"cardid": c1_id, "sortorder": 0},
                {"cardid": c2_id, "sortorder": 0},
            ],
        )
        path = _make_path()
        c1 = _make_card(cardid=c1_id, sortorder=0, parent_ng_id=parent_id)
        c2 = _make_card(cardid=c2_id, sortorder=0, parent_ng_id=parent_id)
        _run(fix_cards=True, doc=doc, path=path, cards=[c1, c2])
        path.write_text.assert_called_once()


# ---------------------------------------------------------------------------
# Command — --fix-nodes
# ---------------------------------------------------------------------------


class TestCommandFixNodes(SimpleTestCase):

    def test_fix_nodes_resolves_duplicate_node_sortorders_exit_zero(self):
        parent_id = _uuid()
        c1_id = _uuid()
        c2_id = _uuid()
        n_parent = _make_node(nodeid=parent_id, sortorder=0)
        n1 = _make_node(nodeid=c1_id, sortorder=0)
        n2 = _make_node(nodeid=c2_id, sortorder=0)
        edges = [(c1_id, parent_id), (c2_id, parent_id)]
        _, _, code = _run(fix_nodes=True, nodes=[n_parent, n1, n2], edges=edges)
        self.assertEqual(code, 0)

    def test_fix_nodes_assigns_unique_sortorders_to_mocks(self):
        parent_id = _uuid()
        c1_id = _uuid()
        c2_id = _uuid()
        n_parent = _make_node(nodeid=parent_id, sortorder=0)
        n1 = _make_node(nodeid=c1_id, sortorder=0)
        n2 = _make_node(nodeid=c2_id, sortorder=0)
        edges = [(c1_id, parent_id), (c2_id, parent_id)]
        _run(fix_nodes=True, nodes=[n_parent, n1, n2], edges=edges)
        self.assertNotEqual(n1.sortorder, n2.sortorder)

    def test_fix_nodes_resolves_null_sortorder(self):
        parent_id = _uuid()
        child_id = _uuid()
        n_parent = _make_node(nodeid=parent_id, sortorder=0)
        n_child = _make_node(nodeid=child_id, sortorder=None)
        edges = [(child_id, parent_id)]
        _, _, code = _run(fix_nodes=True, nodes=[n_parent, n_child], edges=edges)
        self.assertEqual(code, 0)

    def test_fix_flag_implies_fix_nodes(self):
        parent_id = _uuid()
        c1_id = _uuid()
        c2_id = _uuid()
        n_parent = _make_node(nodeid=parent_id, sortorder=0)
        n1 = _make_node(nodeid=c1_id, sortorder=0)
        n2 = _make_node(nodeid=c2_id, sortorder=0)
        edges = [(c1_id, parent_id), (c2_id, parent_id)]
        _, _, code = _run(fix=True, nodes=[n_parent, n1, n2], edges=edges)
        self.assertEqual(code, 0)

    def test_fix_nodes_null_last_strategy(self):
        # Items with existing unique sortorders keep their order; NULLs go last.
        parent_id = _uuid()
        ids = [_uuid() for _ in range(3)]
        n_parent = _make_node(nodeid=parent_id, sortorder=0)
        n_first = _make_node(nodeid=ids[0], sortorder=0, name="First")
        n_second = _make_node(nodeid=ids[1], sortorder=1, name="Second")
        n_null = _make_node(nodeid=ids[2], sortorder=None, name="NullNode")
        edges = [(ids[0], parent_id), (ids[1], parent_id), (ids[2], parent_id)]
        _run(fix_nodes=True, nodes=[n_parent, n_first, n_second, n_null], edges=edges)
        # After fix: First=0, Second=1, Null=2 (assigned last)
        self.assertGreater(n_null.sortorder, n_first.sortorder)
        self.assertGreater(n_null.sortorder, n_second.sortorder)


# ---------------------------------------------------------------------------
# Command — --align-nodes
# ---------------------------------------------------------------------------


class TestCommandAlignNodes(SimpleTestCase):

    def test_align_nodes_blocked_when_widgets_have_problems(self):
        card_id = _uuid()
        w1 = _make_widget(card_id=card_id, sortorder=None, card_name="Section Overview")
        out, _, _ = _run(align_nodes=True, widgets=[w1])
        self.assertIn("blocked", out.lower())

    def test_align_nodes_blocked_message_names_the_card(self):
        card_id = _uuid()
        w1 = _make_widget(card_id=card_id, sortorder=None, card_name="Section Overview")
        out, _, _ = _run(align_nodes=True, widgets=[w1])
        self.assertIn("Section Overview", out)

    def test_align_nodes_blocked_message_deferred_after_problem_groups(self):
        # Node problem should appear before the deferred blocked message in output.
        parent_id = _uuid()
        child1_id = _uuid()
        child2_id = _uuid()
        card_id = _uuid()

        n_parent = _make_node(nodeid=parent_id, sortorder=0, name="ParentNode")
        n1 = _make_node(nodeid=child1_id, sortorder=0, name="ChildOne")
        n2 = _make_node(nodeid=child2_id, sortorder=0, name="ChildTwo")
        edges = [(child1_id, parent_id), (child2_id, parent_id)]
        # Use a card name without "blocked" so substring matching is unambiguous.
        w = _make_widget(card_id=card_id, sortorder=None, card_name="SectionOverview")

        out, _, _ = _run(
            align_nodes=True,
            nodes=[n_parent, n1, n2],
            edges=edges,
            widgets=[w],
        )
        # The deferred "--align-nodes blocked" message must appear after the
        # node problem group, not interleaved with it.
        self.assertIn("ChildOne", out)
        self.assertIn("--align-nodes blocked", out)
        self.assertLess(out.index("ChildOne"), out.index("--align-nodes blocked"))

    def test_align_nodes_aligns_widget_nodes_when_widgets_are_clean(self):
        # With clean widgets, alignment should run and update node sortorders.
        parent_id = _uuid()
        node1_id = _uuid()
        node2_id = _uuid()

        n_parent = _make_node(nodeid=parent_id, sortorder=0)
        # Both children have sortorder=0 (duplicate) but widgets are clean.
        n1 = _make_node(nodeid=node1_id, sortorder=0, name="FieldOne")
        n2 = _make_node(nodeid=node2_id, sortorder=0, name="FieldTwo")
        edges = [(node1_id, parent_id), (node2_id, parent_id)]

        # widget_so maps node_id → sortorder for the align-nodes lookup
        widget_so = [(node1_id, 0), (node2_id, 1)]

        _, _, code = _run(
            align_nodes=True,
            nodes=[n_parent, n1, n2],
            edges=edges,
            widget_so=widget_so,
        )
        # After alignment, duplicate sortorders should be resolved.
        self.assertNotEqual(n1.sortorder, n2.sortorder)
        self.assertEqual(code, 0)

    def test_align_nodes_does_not_exit_nonzero_after_alignment(self):
        parent_id = _uuid()
        node1_id = _uuid()
        node2_id = _uuid()
        n_parent = _make_node(nodeid=parent_id, sortorder=0)
        n1 = _make_node(nodeid=node1_id, sortorder=0)
        n2 = _make_node(nodeid=node2_id, sortorder=0)
        edges = [(node1_id, parent_id), (node2_id, parent_id)]
        widget_so = [(node1_id, 0), (node2_id, 1)]

        _, _, code = _run(
            align_nodes=True,
            nodes=[n_parent, n1, n2],
            edges=edges,
            widget_so=widget_so,
        )
        self.assertEqual(code, 0)


# ---------------------------------------------------------------------------
# Command — deferred output ordering
# ---------------------------------------------------------------------------


class TestCommandDeferredOutput(SimpleTestCase):

    def test_updated_path_printed_after_problem_groups(self):
        # When --fix-cards resolves a card problem the "updated: ..." line
        # must appear after the problem group listing, not interleaved.
        parent_id = _uuid()
        cid = _uuid()
        json_card = {"cardid": cid, "sortorder": 0}
        doc = _make_doc(_uuid(), cards=[json_card])
        path = _make_path(relative="bcap/pkg/graphs/resource_models/MyGraph.json")

        c1 = _make_card(
            cardid=cid, sortorder=0, name="CardAlpha", parent_ng_id=parent_id
        )
        c2 = _make_card(sortorder=0, name="CardBeta", parent_ng_id=parent_id)

        out, _, _ = _run(fix_cards=True, doc=doc, path=path, cards=[c1, c2])

        self.assertIn("CardAlpha", out)
        self.assertIn("updated", out.lower())
        self.assertLess(out.index("CardAlpha"), out.lower().index("updated"))

    def test_updated_path_includes_relative_filename(self):
        parent_id = _uuid()
        c1_id = _uuid()
        c2_id = _uuid()
        # Both card IDs must be in the doc so the changed card sets graph_dirty.
        doc = _make_doc(
            _uuid(),
            cards=[
                {"cardid": c1_id, "sortorder": 0},
                {"cardid": c2_id, "sortorder": 0},
            ],
        )
        path = _make_path(relative="bcap/pkg/graphs/resource_models/MyGraph.json")

        c1 = _make_card(cardid=c1_id, sortorder=0, parent_ng_id=parent_id)
        c2 = _make_card(cardid=c2_id, sortorder=0, parent_ng_id=parent_id)

        out, _, _ = _run(fix_cards=True, doc=doc, path=path, cards=[c1, c2])
        self.assertIn("MyGraph.json", out)


# ---------------------------------------------------------------------------
# Command — --resource-models-only flag
# ---------------------------------------------------------------------------


class TestCommandResourceModelsOnly(SimpleTestCase):

    def test_resource_models_only_passed_to_generator(self):
        received = []

        def _fake(resource_models_only=False):
            received.append(resource_models_only)
            return iter([])

        with (
            patch(f"{_MODULE}._all_package_graphs", side_effect=_fake),
            patch(f"{_MODULE}.settings") as ms,
        ):
            ms.APP_ROOT = "/fake"
            call_command(
                "check_card_sortorders",
                resource_models_only=True,
                stdout=StringIO(),
                stderr=StringIO(),
                no_color=True,
            )

        self.assertEqual(received, [True])

    def test_without_flag_passes_false_to_generator(self):
        received = []

        def _fake(resource_models_only=False):
            received.append(resource_models_only)
            return iter([])

        with (
            patch(f"{_MODULE}._all_package_graphs", side_effect=_fake),
            patch(f"{_MODULE}.settings") as ms,
        ):
            ms.APP_ROOT = "/fake"
            call_command(
                "check_card_sortorders",
                stdout=StringIO(),
                stderr=StringIO(),
                no_color=True,
            )

        self.assertEqual(received, [False])
