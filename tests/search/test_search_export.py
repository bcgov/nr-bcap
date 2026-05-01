import codecs
from io import StringIO
from unittest.mock import patch

from django.test import TestCase

from bcap.search.search_export import BCAPSearchResultsExporter

_BOM = codecs.BOM_UTF8.decode("utf-8")


class TestBCAPSearchResultsExporter(TestCase):
    def test_prepend_bom(self):
        result = BCAPSearchResultsExporter._prepend_bom(StringIO("col1,col2\n"))
        self.assertEqual(result.read(), _BOM + "col1,col2\n")

    @patch("arches.app.search.search_export.SearchResultsExporter.to_csv")
    def test_to_csv_prepends_bom(self, mock_super):
        csv_content = "col1,col2\nval1,val2\n"
        mock_super.return_value = {
            "name": "export.csv",
            "outputfile": StringIO(csv_content),
        }
        exporter = object.__new__(BCAPSearchResultsExporter)
        result = exporter.to_csv([], [], "export.csv")
        self.assertEqual(result["outputfile"].read(), _BOM + csv_content)
        self.assertEqual(result["name"], "export.csv")
