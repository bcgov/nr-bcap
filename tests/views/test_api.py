import json
from datetime import timedelta
from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from django.contrib.auth import get_user_model
from oauth2_provider.models import AccessToken, get_application_model


@override_settings(ROOT_URLCONF="bcap.tests.test_urls")
class BordenNumberExternalViewTests(TestCase):
    def setUp(self):
        self.url = reverse("borden-number-external")

        User = get_user_model()
        self.user = User.objects.create_user(
            username="tokenuser",
            password="pass",
            email="tokenuser@example.com",
        )

        Application = get_application_model()
        self.application = Application.objects.create(
            user=self.user,
            name="test-app",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_PASSWORD,
        )

        self.access_token = AccessToken.objects.create(
            user=self.user,
            application=self.application,
            token="test-access-token",
            scope="read write",
            expires=timezone.now() + timedelta(hours=1),
        )

        # Minimal POST data expected by BordenNumberBase._post_impl (form-encoded)
        self.post_data = {
            "site_boundary": json.dumps(
                {"type": "Point", "coordinates": [-123.2, 49.2]}
            ),
            "reserve_borden_number": "false",
        }

    def test_post_requires_bearer_token(self):
        resp = self.client.post(self.url, data=self.post_data)

        # django-oauth-toolkit ProtectedResourceView returns 401 for missing/invalid token
        self.assertEqual(resp.status_code, 403)

    @patch("bcap.views.api.BordenNumberBase._post_impl")
    def test_post_with_valid_token_allows_request(self, post_impl_patch):
        # If auth passes, we should reach _post_impl (avoid real implementation)
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
