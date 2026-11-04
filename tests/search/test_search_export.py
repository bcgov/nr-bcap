import codecs
from io import StringIO
from unittest.mock import MagicMock, patch

from django.test import TestCase

from bcap.search.search_export import BCAPSearchResultsExporter

_BOM = codecs.BOM_UTF8.decode("utf-8")
_MODULE = "bcap.search.search_export"


def _ordered_header(parent_headers, exportable_nodes, export_type="csv"):
    """Run return_ordered_header with mocked super() and Node queryset."""
    exporter = object.__new__(BCAPSearchResultsExporter)
    with (
        patch(
            "arches.app.search.search_export.SearchResultsExporter.return_ordered_header",
            return_value=list(parent_headers),
        ),
        patch(f"{_MODULE}.arches_models") as mock_am,
    ):
        # exportable_nodes is a list of (name, datatype) tuples
        mock_am.Node.objects.filter.return_value.exclude.return_value.values_list.return_value = (
            exportable_nodes
        )
        return exporter.return_ordered_header("graph-uuid", export_type)


class TestReturnOrderedHeader(TestCase):

    def test_non_csv_export_type_is_unchanged(self):
        headers = _ordered_header(["col1"], [("col1", "string")], export_type="json")
        self.assertEqual(headers, ["col1"])

    def test_exportable_node_not_in_headers_is_appended(self):
        headers = _ordered_header(["existing"], [("new_col", "string")])
        self.assertIn("new_col", headers)

    def test_existing_header_is_not_duplicated(self):
        headers = _ordered_header(["col1"], [("col1", "string")])
        self.assertEqual(headers.count("col1"), 1)

    def test_geojson_node_already_in_headers_is_removed(self):
        headers = _ordered_header(
            ["geom_col"],
            [("geom_col", "geojson-feature-collection")],
        )
        self.assertNotIn("geom_col", headers)

    def test_geojson_node_not_in_headers_is_still_added(self):
        # A geojson node that wasn't in the parent headers is a new exportable
        # node — it should be appended, not filtered.
        headers = _ordered_header(
            [],
            [("geom_col", "geojson-feature-collection")],
        )
        self.assertIn("geom_col", headers)

    def test_non_geojson_node_already_in_headers_is_not_removed(self):
        headers = _ordered_header(["string_col"], [("string_col", "string")])
        self.assertIn("string_col", headers)

    def test_original_header_order_is_preserved(self):
        headers = _ordered_header(
            ["first", "second"],
            [("third", "string")],
        )
        self.assertEqual(headers.index("first"), 0)
        self.assertEqual(headers.index("second"), 1)
        self.assertIn("third", headers)

    def test_new_nodes_appended_after_existing_headers(self):
        headers = _ordered_header(["existing"], [("new_col", "string")])
        self.assertGreater(headers.index("new_col"), headers.index("existing"))

    def test_multiple_geojson_nodes_in_headers_all_removed(self):
        headers = _ordered_header(
            ["geom1", "geom2", "text_col"],
            [
                ("geom1", "geojson-feature-collection"),
                ("geom2", "geojson-feature-collection"),
                ("text_col", "string"),
            ],
        )
        self.assertNotIn("geom1", headers)
        self.assertNotIn("geom2", headers)
        self.assertIn("text_col", headers)


class TestBCAPSearchResultsExporter(TestCase):
    def test_prepend_bom(self):
        result = BCAPSearchResultsExporter._prepend_bom(StringIO("col1,col2\n"))
        self.assertEqual(result.read(), _BOM + "col1,col2\n")

    def test_to_csv_prepends_bom(self):
        exporter = object.__new__(BCAPSearchResultsExporter)
        instances = [{"col1": "val1", "col2": "val2"}]
        result = exporter.to_csv(instances, ["col1", "col2"], "export")
        content = result["outputfile"].read()
        self.assertTrue(content.startswith(_BOM))
        self.assertIn("col1,col2", content)
        self.assertIn("val1,val2", content)
        self.assertEqual(result["name"], "export.csv")
