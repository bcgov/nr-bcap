import time
import requests_mock
from unittest.mock import patch
from django.test import TestCase
from authlib.integrations.requests_client import OAuth2Session
from django.conf import settings
from bcgov_arches_common.util.auth import token_store


class BCAPOAuthTestMixin:
    def get_oauth_session_and_config(self, token=None, update_token=None):
        """
        Returns an Authlib OAuth2Session configured to use the BCAP OAuth client config.
        """
        oauth_config = settings.AUTHLIB_OAUTH_CLIENTS["default"]
        return oauth_config, OAuth2Session(
            client_id=oauth_config["client_id"],
            client_secret=oauth_config["client_secret"],
            token=token,
            update_token=update_token or token_store.save_token,
            refresh_token_url=oauth_config["access_token_url"],
            token_endpoint=oauth_config["access_token_url"],
            token_endpoint_auth_method=oauth_config.get(
                "token_endpoint_auth_method", "client_secret_basic"
            ),
        )


class OAuthTokenRefreshTest(TestCase, BCAPOAuthTestMixin):

    @patch(
        "bcgov_arches_common.util.auth.token_store.save_token",
        wraps=token_store.save_token,
    )
    def test_refresh_triggers_save_token(self, spy_save_token):
        expired_token = {
            "access_token": "expired-token",
            "refresh_token": "refresh-token",
            "token_type": "Bearer",
            "expires_at": int(time.time()) - 60,
        }

        refreshed_token = {
            "access_token": "new-token",
            "refresh_token": "refresh-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "expires_at": int(time.time()) + 3600,
            "userinfo": {"preferred_username": "test@example.com"},
        }

        oauth_config, session = self.get_oauth_session_and_config(token=expired_token)

        with requests_mock.Mocker() as m:
            m.post(oauth_config["access_token_url"], json=refreshed_token)
            session.refresh_token(oauth_config["access_token_url"])

        spy_save_token.assert_called_once()
        saved_token = spy_save_token.call_args[0][0]
        self.assertEqual(saved_token["access_token"], "new-token")

    def test_refresh_failure_raises_exception(self):
        expired_token = {
            "access_token": "expired-token",
            "refresh_token": "bad-refresh-token",
            "token_type": "Bearer",
            "expires_at": int(time.time()) - 60,
        }

        oauth_config, session = self.get_oauth_session_and_config(token=expired_token)

        with requests_mock.Mocker() as m:
            m.post(
                oauth_config["access_token_url"],
                status_code=400,
                json={"error": "invalid_grant"},
            )

            with self.assertRaises(Exception) as context:
                session.refresh_token(oauth_config["access_token_url"])

            self.assertIn("invalid_grant", str(context.exception))

    def test_expired_session_is_not_valid(self):
        session = self.client.session
        session.set_expiry(-1)  # Force session to expire immediately
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key

        response = self.client.get("/bcap/index.htm", follow=True)
        self.assertNotIn("oauth_token", self.client.session)
