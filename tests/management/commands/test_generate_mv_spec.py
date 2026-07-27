from io import StringIO
from unittest.mock import Mock, mock_open, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from arches.app.models.models import GraphModel

from bcap.management.commands.generate_mv_spec import (
    DATE_FORMAT_DEFAULT,
    _date_format,
    _render_spec,
    _schema_name,
)

# ---------------------------------------------------------------------------
# _schema_name
# ---------------------------------------------------------------------------


class TestSchemaName(SimpleTestCase):
    def test_hyphens_replaced_with_underscores(self):
        self.assertEqual(_schema_name("archaeological-site"), "archaeological_site")

    def test_underscores_unchanged(self):
        self.assertEqual(_schema_name("site_visit"), "site_visit")

    def test_already_a_valid_identifier(self):
        self.assertEqual(_schema_name("hca_permit"), "hca_permit")

    def test_multiple_hyphens(self):
        self.assertEqual(_schema_name("a-b-c-d"), "a_b_c_d")


# ---------------------------------------------------------------------------
# _date_format
# ---------------------------------------------------------------------------


class TestDateFormat(SimpleTestCase):
    def _node(self, config):
        return Mock(config=config)

    def test_date_format_from_camel_case_key(self):
        node = self._node({"dateFormat": "DD/MM/YYYY"})
        self.assertEqual(_date_format(node), "DD/MM/YYYY")

    def test_date_format_from_lowercase_key(self):
        node = self._node({"dateformat": "MM-YYYY"})
        self.assertEqual(_date_format(node), "MM-YYYY")

    def test_camel_case_key_takes_priority_over_lowercase(self):
        node = self._node({"dateFormat": "YYYY", "dateformat": "other"})
        self.assertEqual(_date_format(node), "YYYY")

    def test_fallback_when_config_is_none(self):
        node = self._node(None)
        self.assertEqual(_date_format(node), DATE_FORMAT_DEFAULT)

    def test_fallback_when_config_is_empty_dict(self):
        node = self._node({})
        self.assertEqual(_date_format(node), DATE_FORMAT_DEFAULT)

    def test_fallback_when_key_absent(self):
        node = self._node({"unrelated": "value"})
        self.assertEqual(_date_format(node), DATE_FORMAT_DEFAULT)

    def test_fallback_when_config_is_not_a_dict(self):
        node = self._node("not-a-dict")
        self.assertEqual(_date_format(node), DATE_FORMAT_DEFAULT)

    def test_fallback_when_date_format_is_empty_string(self):
        # Empty string is falsy; should fall back to default.
        node = self._node({"dateFormat": ""})
        self.assertEqual(_date_format(node), DATE_FORMAT_DEFAULT)


# ---------------------------------------------------------------------------
# _render_spec
# ---------------------------------------------------------------------------


class TestRenderSpec(SimpleTestCase):
    # Minimal ng_list used across several tests.
    _GRAPH_ID = "aaaa-0000-bbbb-1111"
    _SCHEMA = "my_schema"
    _NG_LIST = [
        (
            "branch_one",
            "ng-uuid-1",
            None,
            "1",
            [
                ("field_a", "node-uuid-1", "string", None),
                ("start_date", "node-uuid-2", "date", "YYYY-MM-DD"),
            ],
        ),
        ("branch_two", "ng-uuid-2", "branch_one", "n", []),
    ]

    def _render(self, ng_list=None):
        return _render_spec(
            self._GRAPH_ID,
            self._SCHEMA,
            ng_list if ng_list is not None else self._NG_LIST,
        )

    def test_output_ends_with_newline(self):
        self.assertTrue(self._render().endswith("\n"))

    def test_graph_id_present(self):
        self.assertIn(f"GRAPH_ID = '{self._GRAPH_ID}'", self._render())

    def test_schema_present(self):
        self.assertIn(f"SCHEMA   = '{self._SCHEMA}'", self._render())

    def test_ng_list_opened_and_closed(self):
        output = self._render()
        self.assertIn("NG = [", output)
        self.assertTrue(output.strip().endswith("]"))

    def test_nodegroup_with_no_fields_uses_compact_form(self):
        # compact: ('alias','ngid','parent','card',[]),
        output = self._render()
        self.assertIn("('branch_two','ng-uuid-2','branch_one','n',[]),", output)

    def test_nodegroup_with_fields_expands(self):
        output = self._render()
        self.assertIn("('branch_one','ng-uuid-1',None,'1',[", output)

    def test_non_date_field_has_none_datefmt(self):
        output = self._render()
        self.assertIn("('field_a','node-uuid-1','string',None),", output)

    def test_date_field_includes_format_string(self):
        output = self._render()
        self.assertIn("('start_date','node-uuid-2','date','YYYY-MM-DD'),", output)

    def test_top_level_nodegroup_parent_is_none(self):
        # branch_one has no parent -> None literal in output.
        output = self._render()
        self.assertIn("None,'1',[", output)

    def test_child_nodegroup_parent_is_quoted_alias(self):
        # branch_two's parent is branch_one -> 'branch_one' in output.
        output = self._render()
        self.assertIn("'branch_two','ng-uuid-2','branch_one'", output)

    def test_empty_ng_list_produces_valid_output(self):
        output = _render_spec(self._GRAPH_ID, self._SCHEMA, [])
        self.assertIn("NG = [", output)
        self.assertIn("]", output)
        self.assertIn(f"GRAPH_ID = '{self._GRAPH_ID}'", output)

    def test_header_docstring_present(self):
        output = self._render()
        self.assertIn('"""', output)
        self.assertIn("AUTO-GENERATED by `manage.py generate_mv_spec`", output)


# ---------------------------------------------------------------------------
# Command (integration — requires database)
# ---------------------------------------------------------------------------


class TestGenerateMvSpecCommand(TestCase):
    """
    Tests for the full generate_mv_spec management command.

    File-writing is mocked so the test suite does not modify the source tree.
    The database queries run against the real test DB (Arches fixtures loaded).
    """

    # Slug of a graph guaranteed to exist in the test database.
    SLUG = "archaeological_site"

    def _call_mocked(self, slug=None, **kwargs):
        """Run the command with file I/O mocked; return (written_content, stdout)."""
        out = StringIO()
        m = mock_open()
        with patch("builtins.open", m), patch("os.makedirs"):
            call_command(
                "generate_mv_spec",
                "--graph",
                slug or self.SLUG,
                stdout=out,
                **kwargs,
            )
        written = m.return_value.write.call_args[0][0]
        return written, out.getvalue()

    # --- error cases --------------------------------------------------------

    def test_unknown_slug_raises_command_error(self):
        with self.assertRaises(CommandError):
            call_command("generate_mv_spec", "--graph", "no_such_graph_slug")

    # --- file content -------------------------------------------------------

    def test_writes_spec_file(self):
        written, _ = self._call_mocked()
        self.assertTrue(written.strip())

    def test_output_contains_correct_graph_id(self):
        graph = GraphModel.objects.get(slug=self.SLUG)
        written, _ = self._call_mocked()
        self.assertIn(f"GRAPH_ID = '{graph.graphid}'", written)

    def test_output_schema_derived_from_slug(self):
        written, _ = self._call_mocked()
        self.assertIn("SCHEMA   = 'archaeological_site'", written)

    def test_output_is_valid_python_header(self):
        written, _ = self._call_mocked()
        self.assertTrue(written.startswith('"""'))
        self.assertIn("GRAPH_ID", written)
        self.assertIn("SCHEMA", written)
        self.assertIn("NG = [", written)

    def test_known_nodegroup_present(self):
        # identification_and_registration is a top-level branch in this graph.
        written, _ = self._call_mocked()
        self.assertIn("'identification_and_registration'", written)

    def test_known_field_present(self):
        # borden_number is a non-localized-string field in that nodegroup.
        written, _ = self._call_mocked()
        self.assertIn("'borden_number'", written)

    def test_borden_number_datatype_correct(self):
        written, _ = self._call_mocked()
        self.assertIn("'borden-number-datatype'", written)

    def test_date_field_includes_format(self):
        # At least one date field should have a non-None datefmt string.
        written, _ = self._call_mocked()
        # date fields use: ('alias','nodeid','date','YYYY-...')
        self.assertIn("'date','YYYY-", written)

    def test_semantic_nodes_not_in_field_lists(self):
        # 'semantic' should not appear as a datatype value in the NG list.
        written, _ = self._call_mocked()
        # Semantic nodes are structural; they carry no tile value.
        self.assertNotIn("'semantic'", written)

    def test_ng_list_not_empty(self):
        written, _ = self._call_mocked()
        # Strip the closing ] line; the NG list must have at least one entry.
        ng_start = written.index("NG = [")
        ng_body = written[ng_start:]
        self.assertIn("(", ng_body)

    # --- stdout summary -----------------------------------------------------

    def test_stdout_reports_success(self):
        _, stdout = self._call_mocked()
        self.assertIn("Wrote", stdout)

    def test_stdout_reports_graph_name(self):
        _, stdout = self._call_mocked()
        self.assertIn("Graph:", stdout)

    def test_stdout_reports_nodegroup_count(self):
        _, stdout = self._call_mocked()
        self.assertIn("nodegroups:", stdout)

    # --- makedirs called with correct slug subpath --------------------------

    def test_makedirs_called_for_slug_directory(self):
        m = mock_open()
        with patch("builtins.open", m), patch("os.makedirs") as mock_mkdirs:
            call_command("generate_mv_spec", "--graph", self.SLUG)
        # The path passed to makedirs should end with the graph slug.
        created_path = mock_mkdirs.call_args[0][0]
        self.assertTrue(
            created_path.endswith(self.SLUG),
            f"Expected makedirs path to end with '{self.SLUG}', got: {created_path}",
        )
