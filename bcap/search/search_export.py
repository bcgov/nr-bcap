import codecs
from io import StringIO

from arches.app.models import models as arches_models
from arches.app.search.search_export import SearchResultsExporter


class BCAPSearchResultsExporter(SearchResultsExporter):
    """Extends SearchResultsExporter to prepend a UTF-8 BOM to CSV exports so
    that Excel and other Windows tools open the file with correct encoding that
    supports special characters."""

    @staticmethod
    def _prepend_bom(inner):
        return StringIO(codecs.BOM_UTF8.decode("utf-8") + inner.getvalue())

    def return_ordered_header(self, graphid, export_type):
        headers = super().return_ordered_header(graphid, export_type)
        # CardXNodeXWidget only covers widget-bearing nodes, so collector nodes
        # (e.g. resource-instance collectors like publication_reference) that are
        # marked exportable are absent from the parent's result even though
        # flatten_tiles() will emit them into every instance dict.  Appending
        # them here prevents DictWriter from raising ValueError on export.
        if export_type == "csv":
            in_headers = set(headers)
            extras = list(
                arches_models.Node.objects.filter(graph_id=graphid, exportable=True)
                .exclude(datatype="semantic")
                .exclude(name__in=in_headers)
                .values_list("name", flat=True)
            )
            headers.extend(extras)
        return headers

    def to_csv(self, instances, headers, name):
        result = super().to_csv(instances, headers, name)
        result["outputfile"] = self._prepend_bom(result["outputfile"])
        return result
