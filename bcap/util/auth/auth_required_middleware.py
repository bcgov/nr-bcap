from django.http.response import HttpResponseRedirect
from django.contrib.auth.middleware import AuthenticationMiddleware
from arches.app.models.system_settings import settings
import re


def should_bypass_auth(request):
    def _clean_path(path):
        return re.sub(r"^/*", "", re.sub("/*$", "", path))

    def _get_base_url():
        return _clean_path(
            settings.FORCE_SCRIPT_NAME
            if settings.FORCE_SCRIPT_NAME
            else settings.BCGOV_PROXY_PREFIX
        )

    def _get_public_urls():
        if len(AuthRequiredMiddleware._valid_urls) == 0:
            base_url = _get_base_url()
            for suffix in [
                "",
                "/auth",
                "/auth/eoauth_start",
                "/auth/eoauth_cb",
                "/unauthorized",
            ]:
                AuthRequiredMiddleware._valid_urls.append("%s%s" % (base_url, suffix))
        return AuthRequiredMiddleware._valid_urls

    def _is_public_path(path):
        cleaned_path = _clean_path(path)
        return cleaned_path in _get_public_urls()

    request_source = (
        request.META.get("REMOTE_ADDR")
        if request.META.get("HTTP_X_FORWARDED_FOR") is None
        else request.META.get("HTTP_X_FORWARDED_FOR")
    )  # return True
    return (
        _is_public_path(request.path)
        or request_source in settings.AUTH_BYPASS_HOSTS
        and request.META.get("HTTP_USER_AGENT").startswith("node-fetch/1.0")
    )


class AuthRequiredMiddleware(AuthenticationMiddleware):

    def process_request(self, request):
        if not request.user.is_authenticated:
            if not should_bypass_auth(request):
                return HttpResponseRedirect("/%s/" % self._get_base_url())
            else:
                print("Bypassing auth")
        return None
