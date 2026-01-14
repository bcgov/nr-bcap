import os
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from oauth2_provider.models import Application


class EnsureBcrhpOauthCommandTests(TestCase):
    def _get_bcrhp_apps(self):
        return Application.objects.filter(name="BCRHP API").order_by("id")

    @patch("builtins.print")
    def test_creates_app_when_missing_and_env_present(self, print_mock):
        self.assertEqual(self._get_bcrhp_apps().count(), 0)

        with patch.dict(
            os.environ,
            {
                "BCRHP_API_CLIENT_ID": "client-id-123",
                "BCRHP_API_CLIENT_SECRET": "secret-abc",
            },
            clear=False,
        ):
            call_command("ensure_bcrhp_oauth")

        apps = self._get_bcrhp_apps()
        self.assertEqual(apps.count(), 1)

        app = apps.first()
        self.assertEqual(app.client_id, "client-id-123")
        self.assertEqual(app.client_type, "confidential")
        self.assertEqual(app.authorization_grant_type, "client-credentials")

        # Secret is often hashed by DOT; don't assert exact equality.
        self.assertTrue(app.client_secret)

        # No error prints expected in this happy-path case
        printed = " ".join(
            " ".join(map(str, c.args)) for c in print_mock.call_args_list
        )
        self.assertNotIn("must be set", printed)

    @patch("builtins.print")
    def test_does_not_create_when_client_id_missing(self, print_mock):
        self.assertEqual(self._get_bcrhp_apps().count(), 0)

        with patch.dict(
            os.environ,
            {
                # Missing BCRHP_API_CLIENT_ID on purpose
                "BCRHP_API_CLIENT_SECRET": "secret-abc",
            },
            clear=False,
        ):
            call_command("ensure_bcrhp_oauth")

        self.assertEqual(self._get_bcrhp_apps().count(), 0)

        # Should print message about missing client id
        print_mock.assert_called()
        printed = " ".join(
            " ".join(map(str, c.args)) for c in print_mock.call_args_list
        )
        self.assertIn("BCRHP_API_CLIENT_ID environment variable must be set", printed)

    @patch("builtins.print")
    def test_updates_secret_when_single_app_exists(self, print_mock):
        app = Application.objects.create(
            name="BCRHP API",
            client_id="client-id-123",
            client_type="confidential",
            authorization_grant_type="client-credentials",
            client_secret="old-secret",
        )

        with patch.dict(
            os.environ,
            {"BCRHP_API_CLIENT_SECRET": "new-secret"},
            clear=False,
        ):
            call_command("ensure_bcrhp_oauth")

        app.refresh_from_db()

        # If django-oauth-toolkit hashes secrets, check_secret may exist.
        if hasattr(app, "check_secret"):
            self.assertTrue(app.check_secret("new-secret"))
        else:
            # Fallback: at least confirm it changed
            self.assertNotEqual(app.client_secret, "old-secret")
            self.assertTrue(app.client_secret)

        # No "must be set" print expected when secret provided
        printed = " ".join(
            " ".join(map(str, c.args)) for c in print_mock.call_args_list
        )
        self.assertNotIn("must be set", printed)

    @patch("builtins.print")
    def test_multiple_apps_prints_warning_and_does_not_update(self, print_mock):
        a1 = Application.objects.create(
            name="BCRHP API",
            client_id="id1",
            client_type="confidential",
            authorization_grant_type="client-credentials",
            client_secret="secret1",
        )
        a2 = Application.objects.create(
            name="BCRHP API",
            client_id="id2",
            client_type="confidential",
            authorization_grant_type="client-credentials",
            client_secret="secret2",
        )

        # Secrets are typically hashed on save; capture the stored values so we can
        # assert they were NOT modified by the command.
        a1.refresh_from_db()
        a2.refresh_from_db()
        a1_secret_before = a1.client_secret
        a2_secret_before = a2.client_secret

        with patch.dict(
            os.environ,
            {"BCRHP_API_CLIENT_SECRET": "new-secret"},
            clear=False,
        ):
            call_command("ensure_bcrhp_oauth")

        a1.refresh_from_db()
        a2.refresh_from_db()

        # Should not have updated either secret in the >1 apps branch
        self.assertEqual(a1.client_secret, a1_secret_before)
        self.assertEqual(a2.client_secret, a2_secret_before)

        printed = " ".join(
            " ".join(map(str, c.args)) for c in print_mock.call_args_list
        )
        self.assertIn("More than one BCRHP API application found", printed)
