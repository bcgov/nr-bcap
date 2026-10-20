import codecs
import csv
from arches.app.search.search_export import sanitize_csv_value
from io import StringIO, BytesIO

from django.contrib.gis.geos import GeometryCollection
from django.contrib.gis.gdal import SpatialReference

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
                {k: sanitize_csv_value(str(v)) for k, v in list(instance.items())}
            )

        return {"name": f"{name}.csv", "outputfile": self._prepend_bom(dest)}
