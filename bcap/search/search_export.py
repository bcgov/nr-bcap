import codecs
from io import StringIO

from arches.app.search.search_export import SearchResultsExporter


class BCAPSearchResultsExporter(SearchResultsExporter):
    """Extends SearchResultsExporter to prepend a UTF-8 BOM to CSV exports so
    that Excel and other Windows tools open the file with correct encoding that
    supports special characters."""

    @staticmethod
    def _prepend_bom(inner):
        return StringIO(codecs.BOM_UTF8.decode("utf-8") + inner.getvalue())

    def to_csv(self, instances, headers, name):
        result = super().to_csv(instances, headers, name)
        result["outputfile"] = self._prepend_bom(result["outputfile"])
        return result
