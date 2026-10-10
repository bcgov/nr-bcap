import codecs
from copy import deepcopy
from io import StringIO
from unittest.mock import MagicMock, patch

import shapefile
from django.contrib.gis.geos import (
    GeometryCollection,
    LinearRing,
    MultiPolygon,
    Point,
    Polygon,
)
from django.test import RequestFactory, SimpleTestCase

from bcap.search.search_export import BCAPSearchResultsExporter, BCAPShpWriter

_BOM = codecs.BOM_UTF8.decode("utf-8")
_MODULE = "bcap.search.search_export"


class TestShapefilePrecision(SimpleTestCase):
    def test_shapefile_default_precision_is_safe_before_projection(self):
        request = RequestFactory().get("/search/export_results", {"format": "shp"})

        with patch(
            "arches.app.search.search_export.DataTypeFactory", return_value=MagicMock()
        ):
            exporter = BCAPSearchResultsExporter(search_request=request)

        self.assertEqual(exporter.precision, 8)

    def test_shapefile_precision_keeps_synthetic_rounding_displacement_below_one_mm(
        self,
    ):
        request = RequestFactory().get(
            "/search/export_results", {"format": "shp", "precision": "5"}
        )
        with patch(
            "arches.app.search.search_export.DataTypeFactory", return_value=MagicMock()
        ):
            exporter = BCAPSearchResultsExporter(search_request=request)

        source = Point(-123.120712345, 49.282712345, srid=4326)
        safely_rounded = Point(
            round(source.x, exporter.precision),
            round(source.y, exporter.precision),
            srid=4326,
        )
        five_decimal_fallback = Point(round(source.x, 5), round(source.y, 5), srid=4326)
        projected_source = source.clone()
        projected_source.transform(3005)
        safely_rounded.transform(3005)
        five_decimal_fallback.transform(3005)

        self.assertEqual(exporter.precision, 8)
        self.assertLess(projected_source.distance(safely_rounded), 0.001)
        self.assertGreater(projected_source.distance(five_decimal_fallback), 0.1)

    def test_non_shapefile_default_precision_is_unchanged(self):
        request = RequestFactory().get("/search/export_results", {"format": "geojson"})

        with patch(
            "arches.app.search.search_export.DataTypeFactory", return_value=MagicMock()
        ):
            exporter = BCAPSearchResultsExporter(search_request=request)

        self.assertEqual(exporter.precision, 5)


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


class TestReturnOrderedHeader(SimpleTestCase):

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


class TestBCAPSearchResultsExporter(SimpleTestCase):
    def test_to_shp_projects_copied_geometry_and_emits_epsg_3005_prj(self):
        exporter = object.__new__(BCAPSearchResultsExporter)
        geometry = GeometryCollection(Point(-123.1207, 49.2827), srid=4326)
        instances = [{"resourceid": "resource-1", "geom": geometry}]
        headers = [
            {"fieldname": "resourceid", "datatype": "str"},
            {"fieldname": "geom", "datatype": "geojson-feature-collection"},
            {"fieldname": "note", "datatype": "str"},
        ]
        original_geometry = geometry.clone()
        original_headers = deepcopy(headers)

        with patch(
            "arches.app.utils.data_management.resources.formats.format.DataTypeFactory",
            return_value=MagicMock(),
        ):
            files = exporter.to_shp(instances, headers, "export")

        by_extension = {item["name"].rsplit(".", 1)[1]: item for item in files}
        reader = shapefile.Reader(
            shp=by_extension["shp"]["outputfile"],
            shx=by_extension["shx"]["outputfile"],
            dbf=by_extension["dbf"]["outputfile"],
        )
        expected = original_geometry[0].clone()
        expected.transform(3005)
        self.assertAlmostEqual(reader.shape(0).points[0][0], expected.x, places=6)
        self.assertAlmostEqual(reader.shape(0).points[0][1], expected.y, places=6)
        self.assertIn(
            'PROJCS["NAD83 / BC Albers"',
            by_extension["prj"]["outputfile"].getvalue().decode("utf-8"),
        )
        self.assertEqual(geometry.srid, 4326)
        self.assertEqual(geometry.wkt, original_geometry.wkt)
        self.assertNotIn("note", instances[0])
        self.assertEqual(headers, original_headers)

    def test_to_shp_accepts_three_dimensional_polygon_coordinates(self):
        polygon = Polygon(
            LinearRing(
                (-123.2, 49.2, 10.0),
                (-123.0, 49.2, 20.0),
                (-123.0, 49.4, 30.0),
                (-123.2, 49.4, 40.0),
                (-123.2, 49.2, 10.0),
            ),
            srid=4326,
        )
        geometry = GeometryCollection(polygon, srid=4326)
        instances = [{"resourceid": "resource-1", "geom": geometry}]
        headers = [
            {"fieldname": "resourceid", "datatype": "str"},
            {"fieldname": "geom", "datatype": "geojson-feature-collection"},
        ]

        with patch(
            "arches.app.utils.data_management.resources.formats.format.DataTypeFactory",
            return_value=MagicMock(),
        ):
            files = object.__new__(BCAPSearchResultsExporter).to_shp(
                instances, headers, "export"
            )

        by_extension = {item["name"].rsplit(".", 1)[1]: item for item in files}
        reader = shapefile.Reader(
            shp=by_extension["shp"]["outputfile"],
            shx=by_extension["shx"]["outputfile"],
            dbf=by_extension["dbf"]["outputfile"],
        )
        self.assertEqual(len(reader.shapes()), 1)
        self.assertTrue(geometry.hasz)
        coordinates = list(polygon.coords[0])
        self.assertEqual(
            BCAPShpWriter._orient_ring(coordinates, counterclockwise=False),
            list(reversed(coordinates)),
        )

    def test_to_shp_maps_colliding_and_unicode_fields_to_unique_dbf_names(self):
        geometry = GeometryCollection(Point(-123.1207, 49.2827), srid=4326)
        instances = [
            {
                "geom": geometry,
                "abcdefghijk": "first value",
                "abcdefghijl": "second value",
                "éééééé": "unicode value",
            }
        ]
        headers = [
            {"fieldname": "geom", "datatype": "geojson-feature-collection"},
            {"fieldname": "abcdefghijk", "datatype": "str"},
            {"fieldname": "abcdefghijl", "datatype": "str"},
            {"fieldname": "éééééé", "datatype": "str"},
        ]

        with patch(
            "arches.app.utils.data_management.resources.formats.format.DataTypeFactory",
            return_value=MagicMock(),
        ):
            files = object.__new__(BCAPSearchResultsExporter).to_shp(
                instances, headers, "export"
            )

        by_extension = {item["name"].rsplit(".", 1)[1]: item for item in files}
        reader = shapefile.Reader(
            shp=by_extension["shp"]["outputfile"],
            shx=by_extension["shx"]["outputfile"],
            dbf=by_extension["dbf"]["outputfile"],
            encoding="utf-8",
        )
        field_names = [field[0] for field in reader.fields[1:]]
        self.assertEqual(len(field_names), len(set(field_names)))
        self.assertTrue(all(len(name.encode("utf-8")) <= 10 for name in field_names))
        self.assertCountEqual(
            reader.record(0), ["first value", "second value", "unicode value"]
        )

    def test_to_shp_emits_utf8_cpg_for_each_shapefile(self):
        geometry = GeometryCollection(
            Point(-123.1207, 49.2827),
            Polygon(
                LinearRing(
                    (-123.2, 49.2),
                    (-123.0, 49.2),
                    (-123.0, 49.4),
                    (-123.2, 49.4),
                    (-123.2, 49.2),
                )
            ),
            srid=4326,
        )
        instances = [{"resourceid": "resource-1", "geom": geometry}]
        headers = [
            {"fieldname": "resourceid", "datatype": "str"},
            {"fieldname": "geom", "datatype": "geojson-feature-collection"},
        ]

        with patch(
            "arches.app.utils.data_management.resources.formats.format.DataTypeFactory",
            return_value=MagicMock(),
        ):
            files = object.__new__(BCAPSearchResultsExporter).to_shp(
                instances, headers, "export"
            )

        shp_stems = {
            item["name"].rsplit(".", 1)[0]
            for item in files
            if item["name"].endswith(".shp")
        }
        cpg_files = {
            item["name"].rsplit(".", 1)[0]: item["outputfile"].getvalue()
            for item in files
            if item["name"].endswith(".cpg")
        }
        self.assertEqual(set(cpg_files), shp_stems)
        self.assertTrue(cpg_files)
        self.assertTrue(all(content == b"UTF-8" for content in cpg_files.values()))

    def test_to_shp_preserves_polygon_holes_and_multipart_geometry(self):
        polygon_with_hole = Polygon(
            LinearRing(
                (-123.2, 49.2),
                (-123.0, 49.2),
                (-123.0, 49.4),
                (-123.2, 49.4),
                (-123.2, 49.2),
            ),
            LinearRing(
                (-123.15, 49.25),
                (-123.15, 49.35),
                (-123.05, 49.35),
                (-123.05, 49.25),
                (-123.15, 49.25),
            ),
        )
        second_polygon = Polygon(
            LinearRing(
                (-122.9, 49.2),
                (-122.8, 49.2),
                (-122.8, 49.3),
                (-122.9, 49.3),
                (-122.9, 49.2),
            )
        )
        geometry = GeometryCollection(
            MultiPolygon(polygon_with_hole, second_polygon), srid=4326
        )
        instances = [{"resourceid": "resource-1", "geom": geometry}]
        headers = [
            {"fieldname": "resourceid", "datatype": "str"},
            {"fieldname": "geom", "datatype": "geojson-feature-collection"},
        ]

        with patch(
            "arches.app.utils.data_management.resources.formats.format.DataTypeFactory",
            return_value=MagicMock(),
        ):
            files = object.__new__(BCAPSearchResultsExporter).to_shp(
                instances, headers, "export"
            )

        by_extension = {item["name"].rsplit(".", 1)[1]: item for item in files}
        reader = shapefile.Reader(
            shp=by_extension["shp"]["outputfile"],
            shx=by_extension["shx"]["outputfile"],
            dbf=by_extension["dbf"]["outputfile"],
        )
        shape = reader.shape(0)
        self.assertEqual(len(shape.parts), 3)
        exported_geometry = shape.__geo_interface__
        self.assertEqual(exported_geometry["type"], "MultiPolygon")
        self.assertEqual(len(exported_geometry["coordinates"]), 2)
        self.assertEqual(len(exported_geometry["coordinates"][0]), 2)

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
