import codecs
import csv
from copy import deepcopy
from io import BytesIO, StringIO

from arches.app.models import models as arches_models
from arches.app.search.search_export import SearchResultsExporter, sanitize_csv_value
from arches.app.utils.data_management.resources.formats.shpfile import ShpWriter
from django.contrib.gis.gdal import SpatialReference
from django.contrib.gis.geos import GeometryCollection
from django.utils.translation import gettext as _


def add_empty_shapefile_export_diagnostic(files, format):
    if format == "shp" and not files:
        diagnostic = StringIO()
        diagnostic.write(
            _(
                "Either no instances were identified for export or no "
                "resources have exportable geometry nodes. Please confirm "
                "that the models of instances you would like to export have "
                "geometry nodes and that those nodes are set as exportable."
            )
        )
        files.append({"name": "error.txt", "outputfile": diagnostic})
    return files


class BCAPShpWriter(ShpWriter):
    """Arches shapefile writer with BC Albers projection metadata."""

    @staticmethod
    def _orient_ring(coordinates, counterclockwise):
        coordinates = list(coordinates)
        signed_area = sum(
            (first[0] * second[1]) - (second[0] * first[1])
            for first, second in zip(coordinates, coordinates[1:])
        )
        if (signed_area > 0) != counterclockwise:
            coordinates.reverse()
        return coordinates

    def convert_geom(self, geos_geom):
        if geos_geom.geom_type == "Polygon":
            polygons = (geos_geom.coords,)
        elif geos_geom.geom_type == "MultiPolygon":
            polygons = geos_geom.coords
        else:
            return super().convert_geom(geos_geom)

        return [
            self._orient_ring(ring, counterclockwise=ring_index > 0)
            for polygon in polygons
            for ring_index, ring in enumerate(polygon)
        ]

    @staticmethod
    def _truncate_utf8(value, maximum_bytes):
        return value.encode("utf-8")[:maximum_bytes].decode("utf-8", errors="ignore")

    @classmethod
    def _dbf_field_mapping(cls, headers):
        mapping = {}
        used = set()
        for header in headers:
            source = header["fieldname"]
            base = source or "field"
            candidate = cls._truncate_utf8(base, 10)
            sequence = 2
            while candidate.casefold() in used:
                suffix = f"_{sequence}"
                candidate = (
                    cls._truncate_utf8(base, 10 - len(suffix.encode("utf-8"))) + suffix
                )
                sequence += 1
            mapping[source] = candidate
            used.add(candidate.casefold())
        return mapping

    def create_shapefiles(self, instances, headers, name):
        field_mapping = self._dbf_field_mapping(headers)
        mapped_headers = deepcopy(headers)
        for header in mapped_headers:
            header["fieldname"] = field_mapping[header["fieldname"]]
        mapped_instances = [
            {field_mapping.get(key, key): value for key, value in instance.items()}
            for instance in instances
        ]

        files = super().create_shapefiles(mapped_instances, mapped_headers, name)
        projection = SpatialReference(3005).wkt.encode("utf-8")
        shapefile_stems = []
        for item in files:
            if item["name"].endswith(".prj"):
                item["outputfile"] = BytesIO(projection)
            elif item["name"].endswith(".shp"):
                shapefile_stems.append(item["name"][:-4])
        files.extend(
            {"name": f"{stem}.cpg", "outputfile": BytesIO(b"UTF-8")}
            for stem in shapefile_stems
        )
        return files


class BCAPSearchResultsExporter(SearchResultsExporter):
    """BCAP-specific CSV and shapefile export behavior."""

    SHAPEFILE_MINIMUM_PRECISION = 8

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.format == "shp":
            self.precision = max(self.precision, self.SHAPEFILE_MINIMUM_PRECISION)

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
        projected_instances = []
        for instance in instances:
            projected_instance = instance.copy()
            for fieldname, value in instance.items():
                if isinstance(value, GeometryCollection):
                    geometry = value.clone()
                    geometry.srid = 4326
                    geometry.transform(3005)
                    projected_instance[fieldname] = geometry
            projected_instances.append(projected_instance)

        writer = BCAPShpWriter()
        return writer.create_shapefiles(projected_instances, deepcopy(headers), name)

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
