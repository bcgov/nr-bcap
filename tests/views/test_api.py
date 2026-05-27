import json
from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from tests.views.helpers import AuthTestHelper


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
