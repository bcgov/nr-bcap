import codecs
import csv
import re
from html.parser import HTMLParser
from arches.app.search.search_export import sanitize_csv_value
from io import StringIO, BytesIO

from django.contrib.gis.geos import GeometryCollection
from django.contrib.gis.gdal import SpatialReference

from arches.app.models import models as arches_models
from arches.app.search.search_export import SearchResultsExporter


class _PlainTextExtractor(HTMLParser):
    """SAX-style HTML → plain text converter.

    Block-level opening tags inject a newline so paragraphs and list items
    start on their own line. <ul> items are prefixed with " - " and <ol>
    items with " N. " (1-based, per nesting level). Inline tags (strong, em,
    a, span …) are silently dropped; their text content is kept.
    convert_charrefs=True (the Python 3 default) automatically decodes
    &amp;, &nbsp;, &#39;, etc. through handle_data.
    """

    _BLOCK = frozenset({"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6"})

    def __init__(self):
        super().__init__()
        self.parts = []
        # Each entry is ["ul"] or ["ol", counter].  Mutable lists so the ol
        # counter can be incremented in place without replacing the entry.
        self._lists = []

    def handle_starttag(self, tag, attrs):
        if tag in self._BLOCK:
            self.parts.append("\n")
        elif tag == "ul":
            self._lists.append(["ul"])
        elif tag == "ol":
            self._lists.append(["ol", 0])
        elif tag == "li":
            self.parts.append("\n")
            if self._lists:
                entry = self._lists[-1]
                if entry[0] == "ul":
                    self.parts.append("\t- ")
                else:
                    entry[1] += 1
                    self.parts.append(f"\t{entry[1]}. ")
            else:
                self.parts.append("\t- ")  # li outside a list context

    def handle_endtag(self, tag):
        if tag in ("ul", "ol") and self._lists:
            self._lists.pop()

    def handle_data(self, data):
        self.parts.append(data)


class BCAPSearchResultsExporter(SearchResultsExporter):
    """Extends SearchResultsExporter to prepend a UTF-8 BOM to CSV exports so
    that Excel and other Windows tools open the file with correct encoding that
    supports special characters."""

    @staticmethod
    def _html_to_text(value, multiline=True):
        """Strip HTML tags from a string, mapping block-level elements to
        newlines. Values that contain no '<' are returned as-is to avoid
        parser overhead on the majority of plain-text fields.

        multiline=False collapses all whitespace runs to single spaces,
        suitable for shapefile DBF fields where newlines cause problems in
        most GIS tools.
        """
        if not isinstance(value, str) or "<" not in value:
            return value
        extractor = _PlainTextExtractor()
        extractor.feed(re.sub(r"\s+", " ", value))
        text = "".join(extractor.parts)
        # Spaces flanking newlines are artefacts of collapsing source whitespace
        # between tags (e.g. "</p> <p>" → "\n \n"). Strip only spaces (not tabs)
        # on each side: tabs after a newline are intentional list indentation.
        text = re.sub(r" *\n *", "\n", text)
        text = re.sub(r"\n{2,}", "\n", text)
        text = text.strip()
        if not multiline:
            return " ".join(text.split())
        return text

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
            exportable = list(
                arches_models.Node.objects.filter(graph_id=graphid, exportable=True)
                .exclude(datatype="semantic")
                .values_list("name", "datatype")
            )
            geojson_in_headers = {
                name
                for name, dt in exportable
                if dt == "geojson-feature-collection" and name in in_headers
            }
            headers = [h for h in headers if h not in geojson_in_headers]
            headers.extend(name for name, _ in exportable if name not in in_headers)
        return headers

    def to_shp(self, instances, headers, name):

        BCALBERS_SRID = 3005

        projected_instances = []
        for instance in instances:
            projected = dict(instance)
            for k, v in projected.items():
                if isinstance(v, GeometryCollection):
                    geom = v.clone()
                    if not geom.srid:
                        geom.srid = 4326
                    geom.transform(BCALBERS_SRID)
                    projected[k] = geom
                else:
                    projected[k] = self._html_to_text(v, multiline=False)
            projected_instances.append(projected)

        files = super().to_shp(projected_instances, headers, name)

        bc_albers_wkt = SpatialReference(BCALBERS_SRID).wkt.encode()
        for f in files:
            if f["name"].endswith(".prj"):
                f["outputfile"] = BytesIO(bc_albers_wkt)

        return files

    def to_csv(self, instances, headers, name):
        """Mirrors the parent implementation with extrasaction='ignore' to drop keys absent from headers."""
        dest = StringIO()
        csvwriter = csv.DictWriter(
            dest, delimiter=",", fieldnames=headers, extrasaction="ignore"
        )
        csvwriter.writeheader()
        for instance in instances:
            csvwriter.writerow(
                {
                    k: sanitize_csv_value(self._html_to_text(str(v)))
                    for k, v in instance.items()
                }
            )

        return {"name": f"{name}.csv", "outputfile": self._prepend_bom(dest)}
