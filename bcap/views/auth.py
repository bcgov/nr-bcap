from django.http import HttpResponse
from django.views.generic import View
from django.shortcuts import render
from django.urls import reverse
from bcap.util.auth.oauth_client import oauth
from bcap.util.auth.oauth_session_control import log_user_in, log_user_out
import logging

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
    log_user_out(request)
    return HttpResponse("Logged out.")
