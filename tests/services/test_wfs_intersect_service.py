"""Tests for WfsIntersectService.

All HTTP calls are mocked via urllib3 so no network access is required.
Arches ORM calls are mocked for the resource_id path. Real GEOS/GDAL is used
for geometry conversion — those libraries are always present in an Arches
environment.
"""

import json
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from bcap.services.wfs.wfs_intersect_service import (
    MissingGeometryError,
    WfsError,
    WfsIntersectService,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

# A simple convex polygon in BC (EPSG:4326).
_POLYGON_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-125.0, 49.0],
            [-124.0, 49.0],
            [-124.0, 50.0],
            [-125.0, 50.0],
            [-125.0, 49.0],
        ]
    ],
}

_FEATURE_GEOJSON = {
    "type": "Feature",
    "geometry": _POLYGON_GEOJSON,
    "properties": {},
}

_FEATURE_COLLECTION_GEOJSON = {
    "type": "FeatureCollection",
    "features": [_FEATURE_GEOJSON],
}

_WFS_RESPONSE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"TENURE_TYPE": "LICENCE", "CROWN_LANDS_FILE": "1234567"},
            "geometry": _POLYGON_GEOJSON,
        }
    ],
}

_LAYER = "WHSE_TANTALIS.TA_CROWN_TENURES_SVW"

# ORM fixture constants
_RESOURCE_ID = "aabbccdd-0000-0000-0000-000000000001"
_NODE_ALIAS = "site_boundary"
_NODE_ID = "nodeid-123"
_NODEGROUP_ID = "ng-456"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_http_response(status=200, body=None):
    if body is None:
        body = json.dumps(_WFS_RESPONSE).encode("utf-8")
    return SimpleNamespace(status=status, data=body)


def _patch_pool(stack, response=None):
    pool = MagicMock()
    pool.request.return_value = response or _mock_http_response()
    cls = stack.enter_context(
        patch(
            "bcap.services.wfs.wfs_intersect_service.urllib3.PoolManager",
            return_value=pool,
        )
    )
    return cls, pool


def _patch_proxy(stack, response=None):
    proxy = MagicMock()
    proxy.request.return_value = response or _mock_http_response()
    cls = stack.enter_context(
        patch(
            "bcap.services.wfs.wfs_intersect_service.urllib3.ProxyManager",
            return_value=proxy,
        )
    )
    return cls, proxy


def _make_node():
    return SimpleNamespace(nodeid=_NODE_ID, nodegroup_id=_NODEGROUP_ID)


def _make_tile(geojson=None):
    return SimpleNamespace(data={_NODE_ID: geojson or _POLYGON_GEOJSON})


def _patch_orm(stack, node, tile):
    """Patch arches_models.Node and TileModel with explicit return values.

    Pass ``None`` for *node* or *tile* to simulate a missing record.
    """
    node_qs = MagicMock()
    node_qs.filter.return_value.first.return_value = node

    tile_qs = MagicMock()
    tile_qs.filter.return_value.first.return_value = tile

    stack.enter_context(
        patch(
            "bcap.services.wfs.wfs_intersect_service.arches_models.Node",
            new=SimpleNamespace(objects=node_qs),
        )
    )
    stack.enter_context(
        patch(
            "bcap.services.wfs.wfs_intersect_service.arches_models.TileModel",
            new=SimpleNamespace(objects=tile_qs),
        )
    )
    return node_qs, tile_qs


# ---------------------------------------------------------------------------
# HTTP mechanics
# ---------------------------------------------------------------------------


class WfsHttpTests(SimpleTestCase):
    def test_query_posts_to_wfs_endpoint(self):
        with ExitStack() as stack:
            _, pool = _patch_pool(stack)
            WfsIntersectService.query(_LAYER, geometry=_POLYGON_GEOJSON)

        pool.request.assert_called_once()
        method, url = pool.request.call_args[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, WfsIntersectService.WFS_ENDPOINT)

    def test_request_carries_xml_content_type(self):
        with ExitStack() as stack:
            _, pool = _patch_pool(stack)
            WfsIntersectService.query(_LAYER, geometry=_POLYGON_GEOJSON)

        headers = pool.request.call_args[1]["headers"]
        self.assertEqual(headers["Content-Type"], "application/xml")

    def test_request_body_contains_layer_name(self):
        with ExitStack() as stack:
            _, pool = _patch_pool(stack)
            WfsIntersectService.query(_LAYER, geometry=_POLYGON_GEOJSON)

        body = pool.request.call_args[1]["body"].decode()
        self.assertIn(_LAYER, body)

    def test_request_body_uses_gml3_poslist_not_gml2_coordinates(self):
        with ExitStack() as stack:
            _, pool = _patch_pool(stack)
            WfsIntersectService.query(_LAYER, geometry=_POLYGON_GEOJSON)

        body = pool.request.call_args[1]["body"].decode()
        self.assertIn("gml:posList", body)
        self.assertNotIn("gml:coordinates", body)
        self.assertNotIn("gml:outerBoundaryIs", body)

    def test_request_body_uses_epsg4326_srs(self):
        with ExitStack() as stack:
            _, pool = _patch_pool(stack)
            WfsIntersectService.query(_LAYER, geometry=_POLYGON_GEOJSON)

        body = pool.request.call_args[1]["body"].decode()
        self.assertIn('srsName="EPSG:4326"', body)
        self.assertNotIn("CRS:84", body)

    def test_request_body_contains_geometry_property(self):
        with ExitStack() as stack:
            _, pool = _patch_pool(stack)
            WfsIntersectService.query(
                _LAYER, geometry=_POLYGON_GEOJSON, geometry_property="SHAPE"
            )

        body = pool.request.call_args[1]["body"].decode()
        self.assertIn("<ogc:PropertyName>SHAPE</ogc:PropertyName>", body)

    def test_default_geometry_property_is_geometry(self):
        with ExitStack() as stack:
            _, pool = _patch_pool(stack)
            WfsIntersectService.query(_LAYER, geometry=_POLYGON_GEOJSON)

        body = pool.request.call_args[1]["body"].decode()
        self.assertIn("<ogc:PropertyName>geometry</ogc:PropertyName>", body)

    def test_returns_parsed_geojson_on_success(self):
        with ExitStack() as stack:
            _patch_pool(stack)
            result = WfsIntersectService.query(_LAYER, geometry=_POLYGON_GEOJSON)

        self.assertEqual(result["type"], "FeatureCollection")
        self.assertEqual(len(result["features"]), 1)
        self.assertEqual(result["features"][0]["properties"]["TENURE_TYPE"], "LICENCE")

    def test_non_200_response_raises_wfs_error(self):
        with ExitStack() as stack:
            _patch_pool(
                stack, response=_mock_http_response(status=503, body=b"unavailable")
            )
            with self.assertRaises(WfsError) as ctx:
                WfsIntersectService.query(_LAYER, geometry=_POLYGON_GEOJSON)

        self.assertIn("503", str(ctx.exception))

    def test_wfs_error_message_includes_layer_name(self):
        with ExitStack() as stack:
            _patch_pool(
                stack, response=_mock_http_response(status=400, body=b"bad request")
            )
            with self.assertRaises(WfsError) as ctx:
                WfsIntersectService.query(_LAYER, geometry=_POLYGON_GEOJSON)

        self.assertIn(_LAYER, str(ctx.exception))

    @override_settings(TILESERVER_OUTBOUND_PROXY="http://proxy.local:3128")
    def test_uses_proxy_manager_when_configured(self):
        with ExitStack() as stack:
            pool_cls, _ = _patch_pool(stack)
            proxy_cls, _ = _patch_proxy(stack)
            WfsIntersectService.query(_LAYER, geometry=_POLYGON_GEOJSON)

        proxy_cls.assert_called_once_with("http://proxy.local:3128")
        pool_cls.assert_not_called()

    @override_settings(TILESERVER_OUTBOUND_PROXY=None)
    def test_uses_pool_manager_without_proxy(self):
        with ExitStack() as stack:
            pool_cls, _ = _patch_pool(stack)
            proxy_cls, _ = _patch_proxy(stack)
            WfsIntersectService.query(_LAYER, geometry=_POLYGON_GEOJSON)

        pool_cls.assert_called_once()
        proxy_cls.assert_not_called()


# ---------------------------------------------------------------------------
# GML 3 rendering (_to_gml3)
# ---------------------------------------------------------------------------


class WfsGml3Tests(SimpleTestCase):
    """Unit tests for _to_gml3 / _ring_poslist — no HTTP involved."""

    def test_polygon_produces_gml3_exterior_poslist(self):
        from django.contrib.gis.geos import GEOSGeometry

        geom = GEOSGeometry(json.dumps(_POLYGON_GEOJSON), srid=4326)
        gml = WfsIntersectService._to_gml3(geom)

        self.assertIn("gml:Polygon", gml)
        self.assertIn("gml:exterior", gml)
        self.assertIn("gml:posList", gml)
        self.assertNotIn("gml:outerBoundaryIs", gml)
        self.assertNotIn("gml:coordinates", gml)

    def test_polygon_carries_epsg4326_srsname(self):
        from django.contrib.gis.geos import GEOSGeometry

        geom = GEOSGeometry(json.dumps(_POLYGON_GEOJSON), srid=4326)
        gml = WfsIntersectService._to_gml3(geom)

        self.assertIn('srsName="EPSG:4326"', gml)

    def test_polygon_coordinates_are_lon_lat(self):
        from django.contrib.gis.geos import GEOSGeometry

        geom = GEOSGeometry(json.dumps(_POLYGON_GEOJSON), srid=4326)
        gml = WfsIntersectService._to_gml3(geom)

        # The first coordinate pair in _POLYGON_GEOJSON is [-125.0, 49.0].
        # In lon/lat order the posList should contain "-125.0 49.0".
        self.assertIn("-125.0 49.0", gml)

    def test_multipolygon_uses_polygon_member_wrapper(self):
        from django.contrib.gis.geos import GEOSGeometry

        fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[-125, 49], [-124, 49], [-124, 50], [-125, 50], [-125, 49]]
                        ],
                    },
                    "properties": {},
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[-123, 49], [-122, 49], [-122, 50], [-123, 50], [-123, 49]]
                        ],
                    },
                    "properties": {},
                },
            ],
        }
        geom = WfsIntersectService._to_geos(fc)
        gml = WfsIntersectService._to_gml3(geom)

        self.assertIn("gml:MultiPolygon", gml)
        self.assertIn("gml:polygonMember", gml)
        self.assertIn('srsName="EPSG:4326"', gml)

    def test_non_polygon_falls_back_to_convex_hull(self):
        from django.contrib.gis.geos import GEOSGeometry

        # A LineString has no area and cannot be used as a polygon filter
        # directly; the service should fall back to its convex hull.
        line = GEOSGeometry(
            '{"type":"LineString","coordinates":[[-125,49],[-124,50],[-123,49]]}',
            srid=4326,
        )
        gml = WfsIntersectService._to_gml3(line)

        self.assertIn("gml:Polygon", gml)
        self.assertIn("gml:posList", gml)


# ---------------------------------------------------------------------------
# Geometry input formats
# ---------------------------------------------------------------------------


class WfsGeometryInputTests(SimpleTestCase):
    def _query(self, **kwargs):
        with ExitStack() as stack:
            _patch_pool(stack)
            return WfsIntersectService.query(_LAYER, **kwargs)

    def test_bare_polygon_geometry(self):
        result = self._query(geometry=_POLYGON_GEOJSON)
        self.assertEqual(result["type"], "FeatureCollection")

    def test_geojson_feature(self):
        result = self._query(geometry=_FEATURE_GEOJSON)
        self.assertEqual(result["type"], "FeatureCollection")

    def test_geojson_feature_collection(self):
        result = self._query(geometry=_FEATURE_COLLECTION_GEOJSON)
        self.assertEqual(result["type"], "FeatureCollection")

    def test_feature_collection_with_multiple_features_is_accepted(self):
        # Two non-overlapping squares; union produces a valid MultiPolygon.
        fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[-125, 49], [-124, 49], [-124, 50], [-125, 50], [-125, 49]]
                        ],
                    },
                    "properties": {},
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[-123, 49], [-122, 49], [-122, 50], [-123, 50], [-123, 49]]
                        ],
                    },
                    "properties": {},
                },
            ],
        }
        result = self._query(geometry=fc)
        self.assertEqual(result["type"], "FeatureCollection")

    def test_empty_feature_collection_raises(self):
        with self.assertRaises(MissingGeometryError):
            self._query(geometry={"type": "FeatureCollection", "features": []})

    def test_feature_without_geometry_raises(self):
        with self.assertRaises(MissingGeometryError):
            self._query(
                geometry={"type": "Feature", "geometry": None, "properties": {}}
            )


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------


class WfsArgumentValidationTests(SimpleTestCase):
    def test_missing_both_raises_missing_geometry_error(self):
        with self.assertRaises(MissingGeometryError):
            WfsIntersectService.query(_LAYER)

    def test_resource_id_without_node_alias_raises_value_error(self):
        with self.assertRaises(ValueError):
            WfsIntersectService.query(_LAYER, resource_id="some-uuid")


# ---------------------------------------------------------------------------
# Resource-id path (Arches ORM)
# ---------------------------------------------------------------------------


class WfsResourceIdTests(SimpleTestCase):
    def test_resolves_geometry_from_resource_and_queries_wfs(self):
        with ExitStack() as stack:
            _patch_orm(stack, node=_make_node(), tile=_make_tile())
            _, pool = _patch_pool(stack)
            result = WfsIntersectService.query(
                _LAYER, resource_id=_RESOURCE_ID, node_alias=_NODE_ALIAS
            )

        pool.request.assert_called_once()
        self.assertEqual(result["type"], "FeatureCollection")

    def test_tile_queried_with_correct_resourceinstance_and_nodegroup(self):
        with ExitStack() as stack:
            _, tile_qs = _patch_orm(stack, node=_make_node(), tile=_make_tile())
            _patch_pool(stack)
            WfsIntersectService.query(
                _LAYER, resource_id=_RESOURCE_ID, node_alias=_NODE_ALIAS
            )

        tile_qs.filter.assert_called_once_with(
            resourceinstance_id=_RESOURCE_ID,
            nodegroup_id=_NODEGROUP_ID,
        )

    def test_unknown_node_alias_raises_missing_geometry_error(self):
        with ExitStack() as stack:
            _patch_orm(stack, node=None, tile=None)
            with self.assertRaises(MissingGeometryError) as ctx:
                WfsIntersectService.query(
                    _LAYER,
                    resource_id=_RESOURCE_ID,
                    node_alias="nonexistent_alias",
                )

        self.assertIn("nonexistent_alias", str(ctx.exception))

    def test_missing_tile_raises_missing_geometry_error(self):
        with ExitStack() as stack:
            _patch_orm(stack, node=_make_node(), tile=None)
            with self.assertRaises(MissingGeometryError) as ctx:
                WfsIntersectService.query(
                    _LAYER, resource_id=_RESOURCE_ID, node_alias=_NODE_ALIAS
                )

        self.assertIn(_RESOURCE_ID, str(ctx.exception))

    def test_tile_with_null_geometry_value_raises(self):
        with ExitStack() as stack:
            _patch_orm(
                stack,
                node=_make_node(),
                tile=SimpleNamespace(data={_NODE_ID: None}),
            )
            with self.assertRaises(MissingGeometryError):
                WfsIntersectService.query(
                    _LAYER, resource_id=_RESOURCE_ID, node_alias=_NODE_ALIAS
                )

    def test_resource_tile_stored_as_feature_collection_is_handled(self):
        """Arches geojson-feature-collection nodes store a FeatureCollection dict."""
        with ExitStack() as stack:
            _patch_orm(
                stack,
                node=_make_node(),
                tile=_make_tile(geojson=_FEATURE_COLLECTION_GEOJSON),
            )
            _, pool = _patch_pool(stack)
            WfsIntersectService.query(
                _LAYER, resource_id=_RESOURCE_ID, node_alias=_NODE_ALIAS
            )

        pool.request.assert_called_once()
