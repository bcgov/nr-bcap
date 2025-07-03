from django.test import TestCase
from authlib.integrations.requests_client import OAuth2Session
import requests_mock
import time
import logging

logger = logging.getLogger(__name__)


class OAuthTokenRefreshTest(TestCase):
    def test_refresh_triggers_update_token(self):
        saved = []

        def save_token(token, request=None, **kwargs):
            saved.append(token)

        expired_token = {
            "access_token": "expired-token",
            "refresh_token": "refresh-token",
            "token_type": "Bearer",
            "expires_at": int(time.time()) - 100,  # expired
        }

        new_token = {
            "access_token": "new-token",
            "refresh_token": "refresh-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "expires_at": int(time.time()) + 3600,
        }

        with requests_mock.Mocker() as m:
            m.post("https://example.com/token", json=new_token)
            m.get(
                "https://api.example.com/userinfo", json={"email": "test@example.com"}
            )

            session = OAuth2Session(
                client_id="my-client",
                client_secret="secret",
                token=expired_token,
                update_token=save_token,
                token_endpoint="https://example.com/token",
                token_endpoint_auth_method="client_secret_basic",
            )

            resp = session.get("https://api.example.com/userinfo")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(saved[0]["access_token"], "new-token")
