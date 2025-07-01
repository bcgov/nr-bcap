import time
import logging
from django.shortcuts import redirect
from django.urls import resolve
from authlib.integrations.requests_client import OAuth2Session
from django.conf import settings
from bcap.util.auth.token_store import save_token

logger = logging.getLogger(__name__)

EXEMPT_PATHS = {
    "/bcap",
    "/bcap/auth",
    "/bcap/auth/eoauth_start",
    "/bcap/auth/eoauth_cb",
    "/bcap/unauthorized",
}


class OAuthTokenRefreshMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.oauth_config = settings.AUTHLIB_OAUTH_CLIENTS["bcap_oauth"]

    def __call__(self, request):
        path = request.path.rstrip("/")
        if path in EXEMPT_PATHS:
            return self.get_response(request)

        expiry_timestamp = request.session.get_expiry_date().timestamp()
        now = time.time()
        time_left = int(expiry_timestamp - now)
        print(f"Session expires in {time_left}")

        token = request.session.get("oauth_token")

        if token:
            expires_at = token.get("expires_at")
            now = time.time()

            if expires_at:
                time_left = int(expires_at - now)
                logger.debug(f"[Token] Time until expiration: {time_left} seconds")

                if expires_at <= now:
                    logger.info("[Token] Expired — attempting refresh")
                    try:
                        session = OAuth2Session(
                            client_id=self.oauth_config["client_id"],
                            client_secret=self.oauth_config["client_secret"],
                            token=token,
                            update_token=save_token,
                            refresh_token_url=self.oauth_config["access_token_url"],
                            token_endpoint=self.oauth_config["access_token_url"],
                            token_endpoint_auth_method=self.oauth_config.get(
                                "token_endpoint_auth_method", "client_secret_basic"
                            ),
                        )

                        new_token = session.refresh_token(
                            self.oauth_config["access_token_url"]
                        )
                        request.session["oauth_token"] = new_token
                        logger.info("[Token] Successfully refreshed token")

                    except Exception as e:
                        logger.error(f"[Token] Failed to refresh: {e}")
                        return redirect("/bcap/unauthorized")

        return self.get_response(request)
