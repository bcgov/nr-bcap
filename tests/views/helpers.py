from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from oauth2_provider.models import AccessToken, get_application_model


class AuthTestHelper:
    """Sets up self.user, self.application, self.access_token for auth tests."""

    def setUp(self):
        super().setUp()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            password="pass",
            email="testuser@example.com",
        )

        Application = get_application_model()
        self.application = Application.objects.create(
            user=self.user,
            name="test-app",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_PASSWORD,
        )

        self.access_token = AccessToken.objects.create(
            user=self.user,
            application=self.application,
            token="test-access-token",
            scope="read write",
            expires=timezone.now() + timedelta(hours=1),
        )

    def idir_login_simulate(self, user=None):
        self.client.force_login(user or self.user)
        session = self.client.session
        expires_at = (timezone.now() + timedelta(hours=1)).timestamp()
        session["oauth_token"] = {"expires_at": expires_at}
        session.save()
