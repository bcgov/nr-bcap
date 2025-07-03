import time
from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import patch
from django.conf import settings
from django.test import override_settings


@override_settings(ROOT_URLCONF="bcap.tests.test_urls")
class OAuthTokenRefreshMiddlewareTest(TestCase):
    def setUp(self):
        self.protected_url = "/test/protected"  # ✅ Now points to a protected route
        self.home_url = "/bcap"
        self.auth_start_url = "/bcap/auth"
        self.unauthorized_url = "/bcap/unauthorized"
        self.session = self.client.session
        self.session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = self.session.session_key

    def test_redirects_to_auth_if_no_token(self):
        """
        If no oauth_token in session, should redirect to OAuth start.
        """
        response = self.client.get(self.protected_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.home_url, response.url)

    # @patch("bcap.views.auth.oauth.bcap_oauth.authorize_access_token")
    # def test_redirects_to_unauthorized_if_user_not_found(self, mock_auth_token):
    #     """
    #     If oauth_token exists but user is missing, redirect to unauthorized.
    #     """
    #     token = {
    #         "access_token": "mock-token",
    #         "refresh_token": "mock-refresh",
    #         "token_type": "Bearer",
    #         "expires_at": int(time.time()) + 3600,
    #         "userinfo": {"preferred_username": "nonexistent@idir"},
    #     }
    #
    #     self.session["oauth_token"] = token
    #     self.session.save()
    #     mock_auth_token.return_value = token
    #
    #     response = self.client.get(self.protected_url, follow=True)
    #     self.assertEqual(response.status_code, 200)
    #     self.assertTemplateUsed(response, "unauthorized.htm")
