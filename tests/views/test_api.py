import json
from unittest.mock import MagicMock, patch

from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from bcap.util.borden_number_api import BordenGridServiceError, MissingGeometryError
from bcap.views.api import BordenNumber
from tests.views.helpers import AuthTestHelper


@override_settings(ROOT_URLCONF="tests.test_urls")
class BordenNumberImplTests(TestCase):
    """Unit tests for BordenNumberBase._get_impl error handling."""

    def setUp(self):
        super().setUp()
        self.view = BordenNumber()
        self.factory = RequestFactory()

    def _call_get_impl(self, exc):
        self.view.api = MagicMock()
        self.view.api.get_next_borden_number.side_effect = exc
        return self.view._get_impl(self.factory.get("/"))

    def test_borden_grid_service_error_returns_error_json_with_message(self):
        exc = BordenGridServiceError(
            "The Borden Grid lookup service returned an unexpected error (HTTP 503). "
            "Please try again or contact system support."
        )
        body = json.loads(self._call_get_impl(exc).content)
        self.assertEqual(body["status"], "error")
        self.assertIn("503", body["message"])

    def test_borden_grid_service_error_is_logged(self):
        exc = BordenGridServiceError("upstream failure")
        with self.assertLogs("bcap.views.api", level="ERROR") as cm:
            self._call_get_impl(exc)
        self.assertTrue(any("upstream failure" in line for line in cm.output))

    def test_missing_geometry_error_returns_error_json_with_message(self):
        exc = MissingGeometryError(
            "No Borden Grid was found for the provided location. "
            "Please ensure the site boundary is within British Columbia."
        )
        body = json.loads(self._call_get_impl(exc).content)
        self.assertEqual(body["status"], "error")
        self.assertIn("British Columbia", body["message"])

    def test_unexpected_exception_returns_generic_error_json(self):
        body = json.loads(self._call_get_impl(RuntimeError("boom")).content)
        self.assertEqual(body["status"], "error")
        self.assertIn("unexpected error", body["message"])


@override_settings(ROOT_URLCONF="tests.test_urls")
class BordenNumberExternalViewTests(AuthTestHelper, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("borden-number-external")
        self.post_data = {
            "site_boundary": json.dumps(
                {"type": "Point", "coordinates": [-123.2, 49.2]}
            ),
            "reserve_borden_number": "false",
        }

    def test_post_requires_bearer_token(self):
        resp = self.client.post(self.url, data=self.post_data)

        # django-oauth-toolkit ProtectedResourceView returns 403 for missing/invalid token
        # django-oauth-toolkit only runs if the auth_exempt_pages is enabled for this route in settings.py
        # Otherwise this is a 302 to homepage.
        self.assertIn(resp.status_code, [302, 403])

    @patch("bcap.views.api.BordenNumberBase._post_impl")
    def test_post_with_valid_token_allows_request(self, post_impl_patch):
        # If auth passes, we should reach _post_impl (avoid real impl)
        post_impl_patch.return_value = HttpResponse(
            json.dumps({"status": "success", "borden_number": "EhRa-001"}),
            content_type="application/json",
        )

        resp = self.client.post(
            self.url,
            data=self.post_data,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token.token}",
        )

        self.assertEqual(resp.status_code, 200)
        post_impl_patch.assert_called_once()
