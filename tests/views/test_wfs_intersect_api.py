"""Tests for WfsIntersectView (bcap/views/wfs_intersect_api.py)."""
from contextlib import ExitStack
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from bcap.services.wfs.wfs_intersect_service import MissingGeometryError, WfsError
from bcap.views.wfs_intersect_api import WfsIntersectView

_MODULE = "bcap.views.wfs_intersect_api"
_LAYER = "WHSE_TANTALIS.TA_CROWN_TENURES_SVW"
_POLYGON = {
    "type": "Polygon",
    "coordinates": [[[-125, 49], [-124, 49], [-124, 50], [-125, 50], [-125, 49]]],
}
_WFS_RESULT = {
    "type": "FeatureCollection",
    "features": [{"type": "Feature", "properties": {"TENURE_TYPE": "LICENCE"}, "geometry": _POLYGON}],
}


class WfsIntersectViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def _post(self, data, *, service_return=None, service_exc=None):
        """POST to the view with authentication bypassed.

        Returns (response, mock_query) where mock_query is the patched
        WfsIntersectService.query callable.
        """
        request = self.factory.post("/", data=data, format="json")
        with ExitStack() as stack:
            stack.enter_context(
                patch.object(WfsIntersectView, "permission_classes", [])
            )
            mock_q = stack.enter_context(
                patch(f"{_MODULE}.WfsIntersectService.query")
            )
            if service_exc is not None:
                mock_q.side_effect = service_exc
            else:
                mock_q.return_value = service_return if service_return is not None else _WFS_RESULT
            response = WfsIntersectView.as_view()(request)
        return response, mock_q

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------

    def test_missing_geometry_returns_400(self):
        response, _ = self._post({"layer": _LAYER})
        self.assertEqual(response.status_code, 400)

    def test_missing_geometry_error_contains_geometry_key(self):
        response, _ = self._post({"layer": _LAYER})
        self.assertIn("geometry", response.data)

    def test_missing_layer_returns_400(self):
        response, _ = self._post({"geometry": _POLYGON})
        self.assertEqual(response.status_code, 400)

    def test_missing_layer_error_contains_layer_key(self):
        response, _ = self._post({"geometry": _POLYGON})
        self.assertIn("layer", response.data)

    def test_missing_both_fields_returns_both_errors(self):
        response, _ = self._post({})
        self.assertEqual(response.status_code, 400)
        self.assertIn("geometry", response.data)
        self.assertIn("layer", response.data)

    def test_missing_fields_service_not_called(self):
        _, mock_q = self._post({"layer": _LAYER})
        mock_q.assert_not_called()

    # ------------------------------------------------------------------
    # Empty FeatureCollection short-circuit
    # ------------------------------------------------------------------

    def test_empty_feature_collection_returns_200(self):
        response, _ = self._post(
            {"geometry": {"type": "FeatureCollection", "features": []}, "layer": _LAYER}
        )
        self.assertEqual(response.status_code, 200)

    def test_empty_feature_collection_returns_empty_features(self):
        response, _ = self._post(
            {"geometry": {"type": "FeatureCollection", "features": []}, "layer": _LAYER}
        )
        self.assertEqual(response.data["type"], "FeatureCollection")
        self.assertEqual(response.data["features"], [])

    def test_empty_feature_collection_service_not_called(self):
        _, mock_q = self._post(
            {"geometry": {"type": "FeatureCollection", "features": []}, "layer": _LAYER}
        )
        mock_q.assert_not_called()

    def test_feature_collection_with_features_calls_service(self):
        fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": _POLYGON, "properties": {}}]}
        _, mock_q = self._post({"geometry": fc, "layer": _LAYER})
        mock_q.assert_called_once()

    # ------------------------------------------------------------------
    # Successful query
    # ------------------------------------------------------------------

    def test_successful_query_returns_200(self):
        response, _ = self._post({"geometry": _POLYGON, "layer": _LAYER})
        self.assertEqual(response.status_code, 200)

    def test_successful_query_returns_service_result(self):
        response, _ = self._post({"geometry": _POLYGON, "layer": _LAYER})
        self.assertEqual(response.data, _WFS_RESULT)

    def test_layer_forwarded_to_service(self):
        _, mock_q = self._post({"geometry": _POLYGON, "layer": _LAYER})
        self.assertEqual(mock_q.call_args[1]["layer"], _LAYER)

    def test_geometry_forwarded_to_service(self):
        _, mock_q = self._post({"geometry": _POLYGON, "layer": _LAYER})
        self.assertEqual(mock_q.call_args[1]["geometry"], _POLYGON)

    def test_geometry_property_defaults_to_geometry(self):
        _, mock_q = self._post({"geometry": _POLYGON, "layer": _LAYER})
        self.assertEqual(mock_q.call_args[1]["geometry_property"], "geometry")

    def test_custom_geometry_property_forwarded_to_service(self):
        _, mock_q = self._post(
            {"geometry": _POLYGON, "layer": _LAYER, "geometry_property": "SHAPE"}
        )
        self.assertEqual(mock_q.call_args[1]["geometry_property"], "SHAPE")

    # ------------------------------------------------------------------
    # Service error handling
    # ------------------------------------------------------------------

    def test_missing_geometry_error_returns_400(self):
        response, _ = self._post(
            {"geometry": _POLYGON, "layer": _LAYER},
            service_exc=MissingGeometryError("no usable geometry"),
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_geometry_error_response_contains_geometry_key(self):
        response, _ = self._post(
            {"geometry": _POLYGON, "layer": _LAYER},
            service_exc=MissingGeometryError("no usable geometry"),
        )
        self.assertIn("geometry", response.data)

    def test_wfs_error_returns_400(self):
        response, _ = self._post(
            {"geometry": _POLYGON, "layer": _LAYER},
            service_exc=WfsError("upstream failed"),
        )
        self.assertEqual(response.status_code, 400)

    def test_wfs_error_response_contains_detail_key(self):
        response, _ = self._post(
            {"geometry": _POLYGON, "layer": _LAYER},
            service_exc=WfsError("upstream failed"),
        )
        self.assertIn("detail", response.data)

    def test_missing_geometry_error_logged_as_warning(self):
        with self.assertLogs(_MODULE, level="WARNING"):
            self._post(
                {"geometry": _POLYGON, "layer": _LAYER},
                service_exc=MissingGeometryError("no geometry"),
            )

    def test_wfs_error_logged_as_error(self):
        with self.assertLogs(_MODULE, level="ERROR"):
            self._post(
                {"geometry": _POLYGON, "layer": _LAYER},
                service_exc=WfsError("upstream failed"),
            )
