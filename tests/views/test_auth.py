"""Tests for auth_callback (bcap/views/auth.py)."""

from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

_MODULE = "bcap.views.auth"


def _call(request, *, token=None, home_page="/home"):
    """Invoke auth_callback with all external dependencies mocked.

    Returns (response, mocks) where mocks is a dict of the patched objects.
    """
    from bcap.views.auth import auth_callback

    token = token or {"access_token": "tok", "userinfo": {"sub": "u1"}}
    mock_service = MagicMock()

    with (
        patch(f"{_MODULE}.oauth") as mock_oauth,
        patch(f"{_MODULE}.InvitationRegistrationService", return_value=mock_service),
        patch(f"{_MODULE}.log_user_in") as mock_login,
        patch(f"{_MODULE}.settings") as mock_settings,
    ):
        mock_oauth.bcgov_oauth.authorize_access_token.return_value = token
        mock_settings.AUTHLIB_OAUTH_CLIENTS = {
            "default": {"urls": {"home_page": home_page}}
        }
        mock_login.return_value = MagicMock(name="login_response")

        response = auth_callback(request)

    return response, {
        "oauth": mock_oauth,
        "service": mock_service,
        "login": mock_login,
    }


class AuthCallbackTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _make_request(self):
        request = self.factory.get("/auth/callback")
        request.session = {}
        return request

    def test_token_stored_in_session(self):
        token = {"access_token": "my-token", "userinfo": {"sub": "user123"}}
        request = self._make_request()
        _call(request, token=token)
        self.assertEqual(request.session["oauth_token"], token)

    def test_ensure_invited_user_called_with_request_and_token(self):
        token = {"access_token": "tok"}
        request = self._make_request()
        _, mocks = _call(request, token=token)
        mocks["service"].ensure_invited_user.assert_called_once_with(request, token)

    def test_log_user_in_called_with_home_page(self):
        request = self._make_request()
        token = {"access_token": "tok"}
        _, mocks = _call(request, token=token, home_page="/dashboard")
        mocks["login"].assert_called_once_with(request, token, "/dashboard")

    def test_redeem_pending_called_after_login(self):
        request = self._make_request()
        _, mocks = _call(request)
        mocks["service"].redeem_pending.assert_called_once_with(request)

    def test_returns_response_from_log_user_in(self):
        request = self._make_request()
        response, mocks = _call(request)
        self.assertIs(response, mocks["login"].return_value)

    def test_home_page_none_when_key_absent(self):
        """settings entry without home_page key → log_user_in receives None."""
        from bcap.views.auth import auth_callback

        token = {"access_token": "tok"}
        request = self._make_request()

        with (
            patch(f"{_MODULE}.oauth") as mock_oauth,
            patch(f"{_MODULE}.InvitationRegistrationService"),
            patch(f"{_MODULE}.log_user_in") as mock_login,
            patch(f"{_MODULE}.settings") as mock_settings,
        ):
            mock_oauth.bcgov_oauth.authorize_access_token.return_value = token
            mock_settings.AUTHLIB_OAUTH_CLIENTS = {
                "default": {"urls": {}}  # no home_page key
            }
            auth_callback(request)

        _, _, home_page_arg = mock_login.call_args[0]
        self.assertIsNone(home_page_arg)
