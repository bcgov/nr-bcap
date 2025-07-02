from django.views.generic import View
from django.contrib.auth import login as system_login, authenticate
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.urls import reverse
from django.contrib.auth.models import User
from bcap.util.auth.oauth_client import oauth
import logging
import re

logger = logging.getLogger(__name__)


class UnauthorizedView(View):
    def get(self, request):
        return render(request, "unauthorized.htm")


def login(request):
    redirect_uri = request.build_absolute_uri(reverse("auth_callback"))
    return oauth.bcap_oauth.authorize_redirect(request, redirect_uri)


def auth_callback(request):
    token = oauth.bcap_oauth.authorize_access_token(request)
    request.session["oauth_token"] = token
    return log_user_in(request, token, "/bcap/index.htm")


def logout(request):
    request.session.pop("oauth_token", None)
    return HttpResponse("Logged out.")


def _clean_username(username):
    # DLVR: IDIR = <username>@idir, TEST, PROD: IDIR = idir\\<username>
    return None if username is None else re.sub(r"^idir\\(.*)$", r"\1@idir", username)


def log_user_in(request, token, next_url):
    logger.debug("In ExternalOauth (custom): %s" % token)
    try:
        username = _clean_username(token["userinfo"]["preferred_username"])
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = None

    if user is not None:
        user.backend = "django.contrib.auth.backends.ModelBackend"
        system_login(
            request,
            user,
        )
        logger.debug("Next URL: %s" % next_url)
        return redirect(next_url)
    else:
        return redirect("unauthorized")
