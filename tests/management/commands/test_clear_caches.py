from io import StringIO
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

_MODULE = "bcap.management.commands.clear_caches"


def _run(caches_setting, side_effects=None, **kwargs):
    """
    Execute the command with a patched settings.CACHES and patched caches[].clear().

    side_effects: dict mapping alias -> exception to raise on clear(), or None for success.
    Returns (stdout_str, stderr_str).
    """
    from django.core.management import call_command

    side_effects = side_effects or {}

    def _make_cache(alias):
        m = MagicMock()
        if alias in side_effects:
            m.clear.side_effect = side_effects[alias]
        return m

    fake_caches = {alias: _make_cache(alias) for alias in caches_setting}

    out, err = StringIO(), StringIO()
    with (
        patch(f"{_MODULE}.settings") as mock_settings,
        patch(f"{_MODULE}.caches", fake_caches),
    ):
        mock_settings.CACHES = caches_setting
        call_command("clear_caches", stdout=out, stderr=err, no_color=True, **kwargs)

    return out.getvalue(), err.getvalue()


class TestClearCachesCommand(SimpleTestCase):

    # ------------------------------------------------------------------
    # No caches configured
    # ------------------------------------------------------------------

    def test_no_caches_reports_nothing_configured(self):
        out, err = _run({})
        self.assertIn("No caches configured", out)
        self.assertEqual(err, "")

    def test_no_caches_does_not_report_done(self):
        out, _ = _run({})
        self.assertNotIn("Done.", out)

    # ------------------------------------------------------------------
    # All caches clear successfully
    # ------------------------------------------------------------------

    def test_clears_single_cache(self):
        fake = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
        _run(fake)  # must not raise

    def test_reports_alias_in_stdout(self):
        fake = {"default": {"BACKEND": "some.Backend"}}
        out, _ = _run(fake)
        self.assertIn("default", out)

    def test_reports_backend_in_stdout(self):
        fake = {"default": {"BACKEND": "some.Backend"}}
        out, _ = _run(fake)
        self.assertIn("some.Backend", out)

    def test_reports_done_with_correct_counts_on_success(self):
        fake = {
            "default": {"BACKEND": "A"},
            "sessions": {"BACKEND": "B"},
        }
        out, _ = _run(fake)
        self.assertIn("Cleared 2, failed 0", out)

    def test_success_summary_goes_to_stdout(self):
        out, err = _run({"default": {"BACKEND": "A"}})
        self.assertIn("Done.", out)
        self.assertNotIn("Done.", err)

    def test_clears_every_alias(self):
        aliases = ["default", "sessions", "views"]
        fake = {a: {"BACKEND": "A"} for a in aliases}
        cleared = []

        def _make_cache(alias):
            m = MagicMock()
            m.clear.side_effect = lambda: cleared.append(alias)
            return m

        fake_caches = {a: _make_cache(a) for a in aliases}
        out, err = StringIO(), StringIO()
        with (
            patch(f"{_MODULE}.settings") as ms,
            patch(f"{_MODULE}.caches", fake_caches),
        ):
            ms.CACHES = fake
            from django.core.management import call_command

            call_command("clear_caches", stdout=out, stderr=err, no_color=True)

        self.assertEqual(sorted(cleared), sorted(aliases))

    def test_missing_backend_key_falls_back_to_unknown(self):
        # A cache entry with no BACKEND key must not crash.
        out, err = _run({"default": {}})
        self.assertIn("unknown backend", out)
        self.assertIn("Cleared 1, failed 0", out)

    # ------------------------------------------------------------------
    # One or more caches fail to clear
    # ------------------------------------------------------------------

    def test_failed_clear_reported_on_stderr(self):
        fake = {"broken": {"BACKEND": "some.Backend"}}
        _, err = _run(fake, side_effects={"broken": RuntimeError("boom")})
        self.assertIn("broken", err)

    def test_failed_clear_includes_exception_class_and_message(self):
        fake = {"broken": {"BACKEND": "B"}}
        _, err = _run(fake, side_effects={"broken": ValueError("bad value")})
        self.assertIn("ValueError", err)
        self.assertIn("bad value", err)

    def test_partial_failure_counts_are_correct(self):
        fake = {
            "default": {"BACKEND": "A"},
            "broken": {"BACKEND": "B"},
        }
        out, err = _run(fake, side_effects={"broken": RuntimeError("boom")})
        self.assertIn("Cleared 1, failed 1", err)

    def test_all_failed_summary_goes_to_stderr(self):
        fake = {"broken": {"BACKEND": "B"}}
        out, err = _run(fake, side_effects={"broken": RuntimeError("x")})
        self.assertIn("Done.", err)
        self.assertNotIn("Done.", out)

    def test_successful_alias_still_reported_to_stdout_on_partial_failure(self):
        fake = {
            "default": {"BACKEND": "A"},
            "broken": {"BACKEND": "B"},
        }
        out, _ = _run(fake, side_effects={"broken": RuntimeError("x")})
        self.assertIn("default", out)
