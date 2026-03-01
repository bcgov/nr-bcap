from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from unittest.mock import patch, MagicMock
from oauth2_provider.models import Application
from django.contrib.auth.hashers import make_password, check_password


class OAuthProviderConfigCommandTests(TestCase):
    def setUp(self):
        """Set up test data"""
        self.name = "Test OAuth App"
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.hashed_client_secret = make_password(self.client_secret)
        self.redirect_uris = "http://example.com/callback"
        self.client_type = "confidential"
        self.authorization_grant_type = "authorization-code"

    @patch.dict("os.environ", {"CLIENT_SECRET": "test_client_secret"})
    def test_add_oauth_config_creates_new_app(self):
        """Test that a new OAuth application is created with the provided parameters"""
        with patch("builtins.input", return_value="y"):
            call_command(
                "oauth_provider_config",
                "--config-name",
                self.name,
                "--client-id",
                self.client_id,
                "--redirect-uris",
                self.redirect_uris,
                "--client-type",
                self.client_type,
                "--grant-type",
                self.authorization_grant_type,
            )

        app = Application.objects.get(client_id=self.client_id)
        self.assertEqual(app.name, self.name)
        self.assertTrue(check_password(self.client_secret, app.client_secret))
        self.assertEqual(app.redirect_uris, self.redirect_uris)
        self.assertEqual(app.client_type, self.client_type)
        self.assertEqual(app.authorization_grant_type, self.authorization_grant_type)

    @patch.dict("os.environ", {"CLIENT_SECRET": "new_secret"})
    def test_update_existing_app_secret(self):
        hashed_secret = make_password("new_secret")
        """Test updating the client secret of an existing application"""
        # Create initial application
        Application.objects.create(
            name=self.name,
            client_id=self.client_id,
            client_secret="old_secret",
            redirect_uris=self.redirect_uris,
            client_type=self.client_type,
            authorization_grant_type=self.authorization_grant_type,
        )

        with patch("builtins.input", return_value="y"):
            call_command(
                "oauth_provider_config",
                "--config-name",
                self.name,
            )

        app = Application.objects.get(client_id=self.client_id)
        self.assertTrue(check_password("new_secret", app.client_secret))

    def test_missing_client_secret_env_var(self):
        """Test that command fails when CLIENT_SECRET environment variable is missing"""
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(CommandError):
                call_command(
                    "oauth_provider_config",
                    "--config-name",
                    self.name,
                    "--client-id",
                    self.client_id,
                )
