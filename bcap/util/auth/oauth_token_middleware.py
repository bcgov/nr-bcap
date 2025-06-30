import time
import logging
from django.shortcuts import redirect
from django.contrib.auth.models import AnonymousUser
from requests_oauthlib import OAuth2Session
from arches.app.utils.external_oauth_backend import ExternalOauthAuthenticationBackend
from bcap.util.auth.auth_required_middleware import should_bypass_auth

logger = logging.getLogger(__name__)


class OAuthTokenMiddleware:
    UNAUTHENTICATED_REDIRECT = "http://localhost:82/bcap"

    def __init__(
        self,
        get_response,
        # client_id="your-client-id",
        # client_secret="your-client-secret",
        # token_url="https://your-oauth-server.com/token",
    ):
        self.get_response = get_response
        # self.client_id = client_id
        # self.client_secret = client_secret
        # self.token_url = token_url

    def __call__(self, request):
        print("OAuth Token Middleware")
        for key, value in request.session.items():
            print(f"\t{key}: {value}")
        print("\n\n")

        if should_bypass_auth(request):
            return self.get_response(request)

        try:
            print("Getting user...")
            user = getattr(request, "user", None)
            print(f"Got user {user}")
        except AttributeError as e:
            print("Attribute error")

        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            print("No user")
            return redirect(OAuthTokenMiddleware.UNAUTHENTICATED_REDIRECT)

        token_record = ExternalOauthAuthenticationBackend.get_token(request.user)

        if not token_record:
            print("No token")
            return redirect(OAuthTokenMiddleware.UNAUTHENTICATED_REDIRECT)

        def update_token_record(new_token):
            print(f"\n\n\nUpdating token record: {new_token}\n\n\n")
            token_record.access_token = new_token["access_token"]
            token_record.access_token_expiration = new_token["expires_at"]
            if "refresh_token" in new_token:
                token_record.token_record.refresh_token = new_token["refresh_token"]
            token_record.save()

        current_time = time.time()
        oauth2_settings = ExternalOauthAuthenticationBackend.get_oauth2_settings()
        token = {
            "access_token": token_record.access_token,
            "refresh_token": token_record.refresh_token,
            "token_type": "Bearer",
            "expires_in": token_record.access_token_expiration.timestamp()
            - current_time,
        }

        oauth = OAuth2Session(
            client_id=oauth2_settings["app_id"],
            token=token,
            auto_refresh_url=oauth2_settings["token_endpoint"],
            auto_refresh_kwargs={
                "client_id": oauth2_settings["app_id"],
                "client_secret": oauth2_settings["app_secret"],
            },
            token_updater=update_token_record,
        )

        request.oauth_session = oauth
        # logger.warning("Calling oauth.refresh_token")
        # new_token = oauth.refresh_token(oauth2_settings["token_endpoint"])
        # logger.warning(f"new_token: {new_token}")
        return self.get_response(request)
