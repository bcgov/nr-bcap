from django.views.generic import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.shortcuts import render, redirect
from arches.app.views.auth import ExternalOauth as CoreExternalOauth

# from arches.app.utils.external_oauth_backend import ExternalOauthAuthenticationBackend
from bcap.util.external_oauth_backend import ExternalOauthAuthenticationBackend
import logging

logger = logging.getLogger(__name__)


class UnauthorizedView(View):
    def get(self, request):
        return render(request, "unauthorized.htm")


class ExternalOauth(CoreExternalOauth):
    def start(request):
        logger.debug("Starting!!")
        next = request.GET.get("next", reverse("home"))
        username = request.GET.get("username", None)

        token, user = ExternalOauthAuthenticationBackend.get_token_for_username(
            username
        )
        if token is not None and token.access_token_expiration > datetime.now():
            return ExternalOauth.log_user_in(request, user, next)

        authorization_url, state = (
            ExternalOauthAuthenticationBackend.get_authorization_url(request)
        )
        request.session["oauth_state"] = state
        request.session["next"] = next
        request.session["user"] = username
        logger.debug("Redirecting with keys: %s" % request.session.keys())
        for key in request.session.keys():
            logger.debug(f"{key}: {request.session[key]}")
        logger.debug(f"Redirecting to {authorization_url}")
        return redirect(authorization_url, preserve_request=True)

    # Extends view class of the same name in Arches Core. Allows use of custom external oauth class
    # and redirects to unauthorized page, not login page when not authorized
    def callback(request):
        logger.debug("In callback (custom)")
        logger.debug(f"Request: {request}")
        logger.debug(f"Request session: {request.session.keys()}")
        next_url = (
            request.session["next"] if "next" in request.session else reverse("home")
        )
        username = request.session["user"] if "user" in request.session else None
        logger.debug(request.GET)
        logger.debug("Session user (custom): %s" % username)
        user = authenticate(
            request,
            username=username,
            sso_authentication=True,
            oauth_state=request.GET["state"],
        )
        logger.debug("User (custom): %s" % user)
        return ExternalOauth.log_user_in(request, user, next_url)

    @staticmethod
    def log_user_in(request, user, next_url):
        logger.debug("In ExternalOauth (custom): %s" % user)
        if user is not None:
            login(
                request,
                user,
                backend="bcap.util.external_oauth_backend.ExternalOauthAuthenticationBackend",
            )
            logger.debug("Next URL: %s" % next_url)
            return redirect(next_url, preserve_request=True)
        else:
            return redirect("unauthorized")
