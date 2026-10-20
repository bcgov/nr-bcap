import sys
from io import StringIO
from unittest.mock import MagicMock, mock_open, patch

from django.core.management import call_command
from django.test import SimpleTestCase

_MODULE = "bcap.management.commands.regen_python_aliases"


# ---------------------------------------------------------------------------
# _snake_to_camel — pure function, no mocking needed
# ---------------------------------------------------------------------------


class TestSnakeToCamel(SimpleTestCase):

    def _convert(self, s):
        from bcap.management.commands.regen_python_aliases import _snake_to_camel

        return _snake_to_camel(s)

    def test_single_word(self):
        self.assertEqual(self._convert("site"), "Site")

    def test_two_words(self):
        self.assertEqual(self._convert("archaeological_site"), "ArchaeologicalSite")

    def test_three_words(self):
        self.assertEqual(self._convert("site_visit_report"), "SiteVisitReport")

    def test_acronym_hca(self):
        self.assertEqual(self._convert("hca"), "HCA")

    def test_acronym_hca_in_compound(self):
        self.assertEqual(self._convert("hca_report"), "HCAReport")

    def test_acronym_trailing(self):
        self.assertEqual(self._convert("report_hca"), "ReportHCA")


# ---------------------------------------------------------------------------
# _write_alias_class — writes to a file-like object
# ---------------------------------------------------------------------------


class TestWriteAliasClass(SimpleTestCase):

    def _make_node(self, alias):
        n = MagicMock()
        n.alias = alias
        return n

    def _write(self, classname, aliases):
        from bcap.management.commands.regen_python_aliases import _write_alias_class

        out = StringIO()
        nodes = [self._make_node(a) for a in aliases]
        _write_alias_class(out, classname, nodes)
        return out.getvalue()

    def test_class_declaration_present(self):
        out = self._write("MyAliases", ["field_one"])
        self.assertIn("class MyAliases(AbstractAliases):", out)

    def test_constant_uppercased(self):
        out = self._write("MyAliases", ["field_one"])
        self.assertIn('FIELD_ONE = "field_one"', out)

    def test_get_aliases_staticmethod_present(self):
        out = self._write("MyAliases", ["field_one"])
        self.assertIn("def get_aliases()", out)
        self.assertIn("AbstractAliases.get_dict(MyAliases)", out)

    def test_multiple_nodes_all_written(self):
        out = self._write("MyAliases", ["alpha", "beta", "gamma"])
        self.assertIn('ALPHA = "alpha"', out)
        self.assertIn('BETA = "beta"', out)
        self.assertIn('GAMMA = "gamma"', out)

    def test_empty_node_list_still_writes_class(self):
        out = self._write("EmptyAliases", [])
        self.assertIn("class EmptyAliases(AbstractAliases):", out)


# ---------------------------------------------------------------------------
# _print_drift_fix — output via print()
# ---------------------------------------------------------------------------


class TestPrintDriftFix(SimpleTestCase):

    def _call(self, drift_nodes, orphan_nodegroups):
        from bcap.management.commands.regen_python_aliases import _print_drift_fix

        captured = StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            _print_drift_fix(drift_nodes, orphan_nodegroups)
        finally:
            sys.stdout = original
        return captured.getvalue()

    def test_no_output_when_both_empty(self):
        self.assertEqual(self._call([], []), "")

    def test_drift_header_when_drift_nodes_present(self):
        node = MagicMock()
        node.pk = "some-uuid"
        node.alias = "stale_field"
        out = self._call([("my_graph", node)], [])
        self.assertIn("DRIFT FIX", out)

    def test_drift_alias_in_output(self):
        node = MagicMock()
        node.pk = "some-uuid"
        node.alias = "stale_field"
        out = self._call([("my_graph", node)], [])
        self.assertIn("stale_field", out)

    def test_orphan_nodegroup_id_in_output(self):
        ng = MagicMock()
        ng.nodegroupid = "ng-orphan-uuid"
        out = self._call([], [ng])
        self.assertIn("ng-orphan-uuid", out)

    def test_backup_warning_present(self):
        node = MagicMock()
        node.pk = "some-uuid"
        node.alias = "x"
        out = self._call([("slug", node)], [])
        self.assertIn("BACK UP", out)

    def test_node_uuid_in_delete_snippet(self):
        node = MagicMock()
        node.pk = "delete-me-uuid"
        node.alias = "gone"
        out = self._call([("s", node)], [])
        self.assertIn("delete-me-uuid", out)


# ---------------------------------------------------------------------------
# _regen_graph_ids — patches DB and file I/O
# ---------------------------------------------------------------------------


def _mock_graph_queryset(graphs, mock_am):
    """Wire up the Graph queryset chain with the given list of {slug, graphid} dicts."""
    (
        mock_am.Graph.objects.exclude.return_value.exclude.return_value.filter.return_value.filter.return_value.values.return_value.order_by.return_value
    ) = graphs


class TestRegenGraphIds(SimpleTestCase):

    def _run(self, graphs, existing_content):
        from bcap.management.commands.regen_python_aliases import _regen_graph_ids

        m = mock_open(read_data=existing_content)
        with (
            patch(f"{_MODULE}.arches_models") as mock_am,
            patch("builtins.open", m),
        ):
            _mock_graph_queryset(graphs, mock_am)
            _regen_graph_ids()

        # Collect everything written to the file
        written = "".join(str(c.args[0]) for c in m.return_value.write.call_args_list)
        return written

    def test_class_graphids_written(self):
        written = self._run(
            [{"slug": "my_graph", "graphid": "aaaa-bbbb"}],
            "existing content\n",
        )
        self.assertIn("class GraphIds:", written)

    def test_slug_constant_uppercased(self):
        written = self._run(
            [{"slug": "my_graph", "graphid": "aaaa-bbbb"}],
            "class GraphIds:\n    OLD = 'x'\n",
        )
        self.assertIn('MY_GRAPH = "aaaa-bbbb"', written)

    def test_replaces_old_constant(self):
        written = self._run(
            [{"slug": "new_graph", "graphid": "new-uuid"}],
            "class GraphIds:\n    OLD_GRAPH = 'old-uuid'\n",
        )
        self.assertNotIn("OLD_GRAPH", written)
        self.assertIn("NEW_GRAPH", written)

    def test_appends_class_when_not_present(self):
        written = self._run(
            [{"slug": "site", "graphid": "site-uuid"}],
            "from bcap.util.bcap_aliases import AbstractAliases\n",
        )
        self.assertIn("class GraphIds:", written)
        self.assertIn('SITE = "site-uuid"', written)

    def test_multiple_graphs_all_written(self):
        written = self._run(
            [
                {"slug": "alpha", "graphid": "uuid-a"},
                {"slug": "beta", "graphid": "uuid-b"},
            ],
            "",
        )
        self.assertIn('ALPHA = "uuid-a"', written)
        self.assertIn('BETA = "uuid-b"', written)


# ---------------------------------------------------------------------------
# _orphan_nodegroups — patches arches_models
# ---------------------------------------------------------------------------


class TestOrphanNodegroups(SimpleTestCase):

    def test_returns_empty_when_no_nodegroups(self):
        from bcap.management.commands.regen_python_aliases import _orphan_nodegroups

        with patch(f"{_MODULE}.arches_models") as mock_am:
            mock_am.NodeGroup.objects.all.return_value = []
            result = _orphan_nodegroups()

        self.assertEqual(result, [])

    def test_skips_nodegroup_that_has_nodes(self):
        from bcap.management.commands.regen_python_aliases import _orphan_nodegroups

        ng = MagicMock()
        ng.nodegroupid = "ng-1"

        with patch(f"{_MODULE}.arches_models") as mock_am:
            mock_am.NodeGroup.objects.all.return_value = [ng]
            mock_am.Node.objects.filter.return_value.exists.return_value = True
            result = _orphan_nodegroups()

        self.assertEqual(result, [])

    def test_skips_nodegroup_with_tiles_but_no_nodes(self):
        from bcap.management.commands.regen_python_aliases import _orphan_nodegroups

        ng = MagicMock()
        ng.nodegroupid = "ng-1"

        with patch(f"{_MODULE}.arches_models") as mock_am:
            mock_am.NodeGroup.objects.all.return_value = [ng]
            mock_am.Node.objects.filter.return_value.exists.return_value = False
            mock_am.TileModel.objects.filter.return_value.count.return_value = 3
            result = _orphan_nodegroups()

        self.assertEqual(result, [])

    def test_returns_nodegroup_with_no_nodes_no_tiles(self):
        from bcap.management.commands.regen_python_aliases import _orphan_nodegroups

        ng = MagicMock()
        ng.nodegroupid = "ng-orphan"

        with patch(f"{_MODULE}.arches_models") as mock_am:
            mock_am.NodeGroup.objects.all.return_value = [ng]
            mock_am.Node.objects.filter.return_value.exists.return_value = False
            mock_am.TileModel.objects.filter.return_value.count.return_value = 0
            result = _orphan_nodegroups()

        self.assertEqual(result, [ng])

    def test_multiple_nodegroups_only_orphan_returned(self):
        from bcap.management.commands.regen_python_aliases import _orphan_nodegroups

        ng_has_nodes = MagicMock()
        ng_has_nodes.nodegroupid = "ng-has-nodes"
        ng_orphan = MagicMock()
        ng_orphan.nodegroupid = "ng-orphan"

        def _node_exists(nodegroup_id=None, **kw):
            m = MagicMock()
            m.exists.return_value = nodegroup_id == ng_has_nodes.nodegroupid
            return m

        def _tile_count(nodegroup_id=None, **kw):
            m = MagicMock()
            m.count.return_value = 0
            return m

        with patch(f"{_MODULE}.arches_models") as mock_am:
            mock_am.NodeGroup.objects.all.return_value = [ng_has_nodes, ng_orphan]
            mock_am.Node.objects.filter.side_effect = _node_exists
            mock_am.TileModel.objects.filter.side_effect = _tile_count
            result = _orphan_nodegroups()

        self.assertNotIn(ng_has_nodes, result)
        self.assertIn(ng_orphan, result)


# ---------------------------------------------------------------------------
# Command.handle — test target switching and high-level delegation
# ---------------------------------------------------------------------------


def _patched_handle(**call_kwargs):
    """Run the command with all expensive helpers mocked out."""
    with (
        patch(f"{_MODULE}._switch_to_test_db") as mock_switch,
        patch(f"{_MODULE}._regen_graph_ids") as mock_regen_ids,
        patch(f"{_MODULE}._orphan_nodegroups", return_value=[]) as mock_orphans,
        patch(f"{_MODULE}._create_alias_file", return_value=[]) as mock_create,
        patch(f"{_MODULE}._json_aliases_by_slug", return_value={}) as mock_json,
        patch(f"{_MODULE}._run_black") as mock_black,
        patch(f"{_MODULE}._print_drift_fix") as mock_drift,
        patch(f"{_MODULE}.os") as mock_os,
        patch(f"{_MODULE}.arches_models") as mock_am,
    ):
        mock_os.listdir.return_value = []
        mock_os.path.join.side_effect = lambda *args: "/".join(args)
        mock_am.Graph.objects.filter.return_value.values_list.return_value = []

        call_command(
            "regen_python_aliases",
            stdout=StringIO(),
            stderr=StringIO(),
            **call_kwargs,
        )

        return {
            "switch": mock_switch,
            "regen_ids": mock_regen_ids,
            "black": mock_black,
        }


class TestHandleTargetSwitch(SimpleTestCase):

    def test_target_test_calls_switch_to_test_db(self):
        mocks = _patched_handle(target="test")
        mocks["switch"].assert_called_once()

    def test_target_dev_does_not_switch_db(self):
        mocks = _patched_handle(target="dev")
        mocks["switch"].assert_not_called()

    def test_default_target_does_not_switch_db(self):
        mocks = _patched_handle()
        mocks["switch"].assert_not_called()

    def test_regen_graph_ids_always_called(self):
        mocks = _patched_handle()
        mocks["regen_ids"].assert_called_once()

    def test_black_called_with_bcap_aliases_path(self):
        mocks = _patched_handle()
        mocks["black"].assert_called_once()
        # The written_files list always includes _BCAP_ALIASES_PATH
        paths_arg = mocks["black"].call_args[0][0]
        self.assertTrue(any("bcap_aliases.py" in str(p) for p in paths_arg))
