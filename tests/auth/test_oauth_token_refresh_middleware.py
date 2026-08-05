from django.test import TestCase
from django.conf import settings
from django.test import override_settings


@override_settings(ROOT_URLCONF="tests.test_urls")
class OAuthTokenRefreshMiddlewareTest(TestCase):
    def setUp(self):
        self.protected_url = "/test/protected"
        self.home_url = "/bcap/"
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
