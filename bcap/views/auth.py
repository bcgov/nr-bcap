"""Authentication entry points that override the library's defaults."""

from django.conf import settings

from bcgov_arches_common.util.auth.oauth_client import oauth
from bcgov_arches_common.util.auth.oauth_session_control import log_user_in

from bcap.services.registration.invitation_registration_service import (
    InvitationRegistrationService,
)


def auth_callback(request):
    """The OAuth redirect handler, overriding the library's so an invited IDIR
    user gets their Django account created before login completes. Access is
    invite-only, so ensure_invited_user creates nothing without a pending token;
    everything else is the library's flow."""
    token = oauth.bcgov_oauth.authorize_access_token(request)
    request.session["oauth_token"] = token
    service = InvitationRegistrationService()
    service.ensure_invited_user(request, token)
    home_page = settings.AUTHLIB_OAUTH_CLIENTS["default"]["urls"].get("home_page")
    response = log_user_in(request, token, home_page)
    service.redeem_pending(request)
    return response
