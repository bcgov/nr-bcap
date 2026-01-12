# bcap/tests/util/test_borden_number_api.py
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db import close_old_connections, connection, connections
from django.test import TestCase, TransactionTestCase, override_settings

from bcap.util.borden_number_api import (
    BordenNumberApi,
    MissingGeometryError,
)


class _FakePoint:
    """
    Minimal stand-in for django.contrib.gis.geos.Point used by BordenNumberApi.
    After transform(), x/y become deterministic for predictable URL assertions.
    """

    def __init__(self, x, y, srid=None):
        self._x = x
        self._y = y
        self.srid = srid

    def transform(self, srid):
        self.srid = srid
        self._x = 100.0
        self._y = 200.0

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y


@override_settings(ROOT_URLCONF="bcap.tests.test_urls")
class BordenNumberApiTests(TestCase):
    def setUp(self):
        self.api = BordenNumberApi()

        # Fake Arches ORM accessors
        self.mock_graph_qs = MagicMock()
        self.mock_node_qs = MagicMock()
        self.mock_tile_qs = MagicMock()

        self.mock_graph = SimpleNamespace()
        self.geom_node = SimpleNamespace(
            nodegroup_id="ng-1",
            nodeid=123,
            datatype="Geometry",
        )
        self.tile_with_geometry = SimpleNamespace(
            data={
                str(self.geom_node.nodeid): {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
                }
            }
        )

        # .objects.filter(...).first() chains
        self.mock_graph_qs.filter.return_value.first.return_value = self.mock_graph
        self.mock_node_qs.filter.return_value.first.return_value = self.geom_node
        self.mock_tile_qs.filter.return_value.first.return_value = (
            self.tile_with_geometry
        )

        # DataTypeFactory mock instance
        self.mock_datatype_factory = MagicMock()
        self.mock_datatype_factory.get_instance.return_value = MagicMock()

        # Geo centroid
        self.centroid = {"coordinates": [-123.123456, 49.123456]}

        # urllib3 fake response
        self.borden_grid_value = "EhRa"
        self.wfs_body = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"BORDGRID": self.borden_grid_value},
                    "geometry": None,
                }
            ],
        }
        self.mock_http_resp = SimpleNamespace(
            data=json.dumps(self.wfs_body).encode("utf-8")
        )

    def _enter_patches(self, stack: ExitStack):
        """
        Register all patches into the provided ExitStack and return a dict
        of the key mocks/handles the tests need to access.
        """
        # Replace Arches models with simple objects that expose `.objects`
        graph_model = SimpleNamespace(objects=self.mock_graph_qs)
        node_model = SimpleNamespace(objects=self.mock_node_qs)
        tile_model = SimpleNamespace(objects=self.mock_tile_qs)

        stack.enter_context(
            patch("bcap.util.borden_number_api.models.GraphModel", new=graph_model)
        )
        stack.enter_context(
            patch("bcap.util.borden_number_api.models.Node", new=node_model)
        )
        stack.enter_context(
            patch("bcap.util.borden_number_api.models.TileModel", new=tile_model)
        )

        # DataTypeFactory returns our mock factory
        dtf_patch = stack.enter_context(
            patch(
                "bcap.util.borden_number_api.DataTypeFactory",
                return_value=self.mock_datatype_factory,
            )
        )

        # GeoUtils class
        geo_utils_cls = stack.enter_context(
            patch("bcap.util.borden_number_api.geo_utils.GeoUtils")
        )
        # Point class
        stack.enter_context(patch("bcap.util.borden_number_api.Point", new=_FakePoint))

        # HTTP managers
        pool_mgr_cls = stack.enter_context(
            patch("bcap.util.borden_number_api.urllib3.PoolManager")
        )
        proxy_mgr_cls = stack.enter_context(
            patch("bcap.util.borden_number_api.urllib3.ProxyManager")
        )

        # Counter
        counter_cls = stack.enter_context(
            patch("bcap.util.borden_number_api.BordenNumberCounter")
        )

        return {
            "dtf_patch": dtf_patch,
            "geo_utils_cls": geo_utils_cls,
            "pool_mgr_cls": pool_mgr_cls,
            "proxy_mgr_cls": proxy_mgr_cls,
            "counter_cls": counter_cls,
        }

    def test_get_next_borden_number_with_resourceinstanceid_calls_peek(self):
        with ExitStack() as stack:
            p = self._enter_patches(stack)

            # centroid
            p["geo_utils_cls"].return_value.get_centroid.return_value = self.centroid

            # no proxy path used
            pool = MagicMock()
            pool.request.return_value = self.mock_http_resp
            p["pool_mgr_cls"].return_value = pool

            p["counter_cls"].peek_next_borden_number.return_value = "EhRa-001"

            result = self.api.get_next_borden_number(resourceinstanceid="ri-1")
            self.assertEqual(result, "EhRa-001")

            # URL built with reprojected coords
            args, _kwargs = pool.request.call_args
            self.assertEqual(args[0], "GET")
            self.assertIn("POINT(100.0%20200.0)", args[1])

            # ensure correct BORDGRID forwarded
            p["counter_cls"].peek_next_borden_number.assert_called_once_with(
                self.borden_grid_value
            )
            # proxy shouldn't be used
            p["proxy_mgr_cls"].assert_not_called()

    def test_get_next_borden_number_with_geometry_direct_calls_peek(self):
        with ExitStack() as stack:
            p = self._enter_patches(stack)

            geometry = {"type": "Point", "coordinates": [-123.2, 49.2]}
            p["geo_utils_cls"].return_value.get_centroid.return_value = self.centroid

            pool = MagicMock()
            pool.request.return_value = self.mock_http_resp
            p["pool_mgr_cls"].return_value = pool

            p["counter_cls"].peek_next_borden_number.return_value = "EhRa-002"

            result = self.api.get_next_borden_number(geometry=geometry)
            self.assertEqual(result, "EhRa-002")

            args, _kwargs = pool.request.call_args
            self.assertEqual(args[0], "GET")
            self.assertIn("POINT(100.0%20200.0)", args[1])

            p["counter_cls"].peek_next_borden_number.assert_called_once_with(
                self.borden_grid_value
            )
            p["proxy_mgr_cls"].assert_not_called()

    def test_get_next_borden_number_raises_when_missing_params(self):
        with ExitStack() as stack:
            self._enter_patches(stack)
            with self.assertRaises(MissingGeometryError):
                self.api.get_next_borden_number()

    def test__get_borden_grid_raises_when_tile_missing(self):
        with ExitStack() as stack:
            p = self._enter_patches(stack)

            # Simulate no tile found: override TileModel.objects.filter().first()
            self.mock_tile_qs.filter.return_value.first.return_value = None

            with self.assertRaises(MissingGeometryError):
                self.api.get_next_borden_number(resourceinstanceid="ri-no-tile")

            # No HTTP calls should be made
            p["pool_mgr_cls"].assert_not_called()
            p["proxy_mgr_cls"].assert_not_called()

    @override_settings(TILESERVER_OUTBOUND_PROXY="http://proxy.local:8080")
    def test_uses_proxy_manager_when_proxy_configured(self):
        with ExitStack() as stack:
            p = self._enter_patches(stack)

            p["geo_utils_cls"].return_value.get_centroid.return_value = self.centroid

            proxy = MagicMock()
            proxy.request.return_value = self.mock_http_resp
            p["proxy_mgr_cls"].return_value = proxy

            p["counter_cls"].peek_next_borden_number.return_value = "EhRa-003"

            result = self.api.get_next_borden_number(resourceinstanceid="ri-proxy")
            self.assertEqual(result, "EhRa-003")

            # Ensure proxy used; direct pool unused
            p["proxy_mgr_cls"].assert_called_once_with("http://proxy.local:8080")
            p["pool_mgr_cls"].assert_not_called()


class BordenNumberApiReserveDbTests(TransactionTestCase):
    """
    DB-backed tests for reserve_borden_number using the configured Postgres DB and
    the real table `bcap_borden_number_counters`.
    """

    @classmethod
    def tearDownClass(cls):
        connections.close_all()
        super().tearDownClass()

    def _fake_grid(self) -> str:
        # borden_grid is max_length=4
        return uuid4().hex[:4].upper()

    def _reset_grid(self, borden_grid: str) -> None:
        # Ensure a clean starting point so expected sequences are deterministic.
        with connection.cursor() as cur:
            cur.execute(
                "DELETE FROM bcap_borden_number_counters WHERE borden_grid = %s",
                [borden_grid],
            )

    @staticmethod
    def _seq_from_borden_number(value: str) -> int:
        # Expected format: "GRID-<int>"
        return int(str(value).rsplit("-", 1)[1])

    def test_reserve_borden_number_increments_each_call(self):
        borden_grid = self._fake_grid()
        self._reset_grid(borden_grid)

        first = BordenNumberApi.reserve_borden_number(borden_grid)
        second = BordenNumberApi.reserve_borden_number(borden_grid)

        self.assertNotEqual(first, second)
        self.assertEqual(self._seq_from_borden_number(first), 1)
        self.assertEqual(self._seq_from_borden_number(second), 2)

    def test_reserve_borden_number_is_thread_safe(self):
        borden_grid = self._fake_grid()
        self._reset_grid(borden_grid)

        n_calls = 40
        barrier = threading.Barrier(n_calls)

        def worker() -> str:
            # Each thread should use a clean connection state.
            close_old_connections()
            try:
                barrier.wait()
                return BordenNumberApi.reserve_borden_number(borden_grid)
            finally:
                connections["default"].close()

        with ThreadPoolExecutor(max_workers=n_calls) as pool:
            results = list(pool.map(lambda _: worker(), range(n_calls)))

        # Core property: no duplicates.
        self.assertEqual(len(results), n_calls)
        self.assertEqual(
            len(set(results)), n_calls, msg=f"Duplicates detected: {results}"
        )

        # Stronger property: because we reset to empty, sequences should be 1..n_calls.
        seqs = sorted(self._seq_from_borden_number(r) for r in results)
        self.assertEqual(seqs, list(range(1, n_calls + 1)))
