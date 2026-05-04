import json
from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from tests.views.helpers import AuthTestHelper

class AuthTestHelper:
    """Sets up self.user, self.application, self.access_token for auth tests."""

    def setUp(self):
        super().setUp()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            password="pass",
            email="testuser@example.com",
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

    def idir_login_simulate(self, user=None):
        self.client.force_login(user or self.user)
        session = self.client.session
        expires_at = (timezone.now() + timedelta(hours=1)).timestamp()
        session["oauth_token"] = {"expires_at": expires_at}
        session.save()


@override_settings(ROOT_URLCONF="bcap.tests.test_urls")
class DashboardViewGetTests(AuthTestHelper, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("dashboard")

    def test_get_unauthenticated(self):
        # No session or token
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        # Fake token
        resp = self.client.get(
            self.url,
            HTTP_AUTHORIZATION="Bearer ABC123",
        )
        self.assertEqual(resp.status_code, 302)

    def test_get_returns_json_cards(self):
        resp = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token.token}",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("Content-Type"), "application/json")
        data = json.loads(resp.content)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        # Extend these tests for various user types when the data model is figured out.

    def test_get_with_session_auth_returns_json_cards(self):
        self.idir_login_simulate()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("Content-Type"), "application/json")
        data = json.loads(resp.content)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)


@override_settings(ROOT_URLCONF="bcap.tests.test_urls")
class BordenNumberExternalViewTests(TestCase):
    def setUp(self):
        super().setUp()
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
