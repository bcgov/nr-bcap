from django.test import TestCase
from unittest.mock import patch
from authlib.integrations.requests_client import OAuth2Session
from bcap.util.auth import token_store
from bcap.util.auth.oauth_client import oauth
from django.conf import settings
import time
import requests_mock


class OAuthTokenRefreshTest2(TestCase):
    @patch("bcap.util.auth.token_store.save_token", wraps=token_store.save_token)
    def test_refresh_triggers_real_save_token(self, spy_save_token):
        expired_token = {
            "access_token": "expired-token",
            "refresh_token": "refresh-token",
            "token_type": "Bearer",
            "expires_at": int(time.time()) - 100,
        }

        refreshed_token = {
            "access_token": "new-token",
            "refresh_token": "refresh-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "expires_at": int(time.time()) + 3600,
            "userinfo": {"preferred_username": "test@example.com"},
        }

        # ✅ Get the original config from Django settings
        oauth_config = settings.AUTHLIB_OAUTH_CLIENTS["bcap_oauth"]

        session = OAuth2Session(
            client_id=oauth_config["client_id"],
            client_secret=oauth_config["client_secret"],
            token=expired_token,
            update_token=token_store.save_token,
            refresh_token_url=oauth_config["access_token_url"],
            token_endpoint=oauth_config["access_token_url"],
            token_endpoint_auth_method=oauth_config.get(
                "token_endpoint_auth_method", "client_secret_basic"
            ),
        )

        with requests_mock.Mocker() as m:
            m.post(oauth_config["access_token_url"], json=refreshed_token)
            session.refresh_token(oauth_config["access_token_url"])

        # ✅ Assert save_token was called
        spy_save_token.assert_called_once()
        saved_token = spy_save_token.call_args[0][0]
        self.assertEqual(saved_token["access_token"], "new-token")
