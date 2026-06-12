from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from oauth2_provider.models import AccessToken, get_application_model


class AuthTestHelper:
    """Sets up cls.user, cls.application, cls.access_token for auth tests.

    Subclasses that define setUpTestData must call super().setUpTestData().
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        User = get_user_model()
        cls.user = User.objects.create_user(
            username="testuser",
            password="pass",
            email="testuser@example.com",
        )

        Application = get_application_model()
        cls.application = Application.objects.create(
            user=cls.user,
            name="test-app",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_PASSWORD,
        )

        cls.access_token = AccessToken.objects.create(
            user=cls.user,
            application=cls.application,
            token="test-access-token",
            scope="read write",
            expires=timezone.now() + timedelta(hours=1),
        )

    def idir_login_simulate(self, user=None, login_source="IDIR"):
        self.client.force_login(user or self.user)
        session = self.client.session
        expires_at = (timezone.now() + timedelta(hours=1)).timestamp()
        session["oauth_token"] = {
            "expires_at": expires_at,
            "userinfo": {"loginSource": login_source},
        }
        session.save()
