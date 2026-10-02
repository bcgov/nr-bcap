"""Unit tests for bc_link_contributors management command.

All database access, service calls, and builder calls are mocked so these
tests run without a real database.
"""

from contextlib import contextmanager
from io import StringIO
from unittest.mock import MagicMock, patch, call

from django.core.management import call_command
from django.test import SimpleTestCase

_MODULE = "bcap.management.commands.bc_link_contributors"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(
    first="Alice",
    last="Smith",
    email="alice@example.com",
    username="asmith",
    *,
    arch_branch=False,
):
    """Build a mock Django User."""
    user = MagicMock()
    user.first_name = first
    user.last_name = last
    user.email = email
    user.username = username
    user.groups.filter.return_value.exists.return_value = arch_branch
    return user


def _make_tile(contributor_id="contrib-uuid", username_value=None, email_value=None):
    """Build a mock TileModel representing a matched contributor record."""
    tile = MagicMock()
    tile.resourceinstance_id = contributor_id
    tile.pk = "tile-pk"
    # data dict keyed by node UUIDs; all node_id() calls are mocked to "node-id"
    tile.data = {
        "node-id": username_value,  # username node
        "email-node-id": email_value,
    }
    return tile


@contextmanager
def _mock_command(
    users=(),
    matched_tile=None,
    org_id="org-uuid",
    set_username_result=True,
):
    """
    Context manager that patches all external dependencies for bc_link_contributors
    and yields a dict of the key mocks.
    """
    with (
        patch(f"{_MODULE}.node_id") as mock_node_id,
        patch(f"{_MODULE}.nodegroup_id") as mock_ng_id,
        patch(f"{_MODULE}.reference_value", return_value="individual-concept"),
        patch(f"{_MODULE}.ContributorService") as mock_svc_cls,
        patch(f"{_MODULE}.ContributorBuilder") as mock_builder_cls,
        patch(f"{_MODULE}.User") as mock_user_cls,
        patch(f"{_MODULE}.TileModel") as mock_tile_cls,
        patch(f"{_MODULE}.ResourceTileTree") as mock_rtt,
        patch(f"{_MODULE}.Resource") as _mock_resource,
        patch(f"{_MODULE}.bulk_index") as mock_bulk_index,
        patch(f"{_MODULE}.localized_string", return_value=None),
        patch(f"{_MODULE}.localized", return_value={"en": {"value": "x"}}),
        patch(
            f"{_MODULE}.resource_instance_value", return_value={"resourceId": org_id}
        ),
        patch(f"{_MODULE}.ContributorSpec") as mock_spec_cls,
    ):
        # node_id / nodegroup_id return predictable strings
        mock_node_id.return_value = "node-id"
        mock_ng_id.return_value = "ng-id"

        # Service
        mock_svc = MagicMock()
        mock_svc.archaeology_branch_id.return_value = org_id
        mock_svc.set_bcap_username.return_value = set_username_result
        mock_svc_cls.return_value = mock_svc

        # Builder
        mock_builder = MagicMock()
        new_contributor = MagicMock()
        new_contributor.pk = "new-contrib-uuid"
        mock_builder.make_contributor.return_value = new_contributor
        mock_builder_cls.return_value = mock_builder

        # Users
        mock_user_cls.objects.all.return_value = list(users)

        # Tile lookup — first() returns matched_tile (or None if no match)
        mock_tile_cls.objects.filter.return_value.first.return_value = matched_tile
        mock_tile_cls.objects.get.return_value = matched_tile  # re-fetch

        # ResourceTileTree (org lookup)
        mock_rtt.get_tiles.return_value.get.return_value = MagicMock()

        yield {
            "svc": mock_svc,
            "builder": mock_builder,
            "bulk_index": mock_bulk_index,
            "tile_cls": mock_tile_cls,
            "spec_cls": mock_spec_cls,
        }


def _run(users=(), dry_run=False, org_id="org-uuid", matched_tile=None, **ctx_kwargs):
    """Run the command and return (stdout_str, mocks_dict)."""
    out = StringIO()
    with _mock_command(
        users=users, matched_tile=matched_tile, org_id=org_id, **ctx_kwargs
    ) as mocks:
        kwargs = {"stdout": out, "stderr": StringIO(), "no_color": True}
        if dry_run:
            kwargs["dry_run"] = True
        call_command("bc_link_contributors", **kwargs)
    return out.getvalue(), mocks


# ---------------------------------------------------------------------------
# Dry-run flag
# ---------------------------------------------------------------------------


class TestDryRun(SimpleTestCase):

    def test_dry_run_prints_banner(self):
        out, _ = _run(dry_run=True)
        self.assertIn("Dry run", out)

    def test_no_dry_run_does_not_print_banner(self):
        out, _ = _run(dry_run=False)
        self.assertNotIn("Dry run", out)

    def test_dry_run_does_not_call_bulk_index(self):
        users = [_make_user()]
        # No tile match → would create contributor
        _, mocks = _run(users=users, dry_run=True)
        mocks["bulk_index"].assert_not_called()

    def test_dry_run_shows_would_create(self):
        users = [_make_user()]
        out, _ = _run(users=users, dry_run=True)
        self.assertIn("dry run", out.lower())


# ---------------------------------------------------------------------------
# Users without a first or last name
# ---------------------------------------------------------------------------


class TestSkippedUsers(SimpleTestCase):

    def test_user_without_first_name_skipped(self):
        user = _make_user(first="")
        out, mocks = _run(users=[user])
        mocks["builder"].make_contributor.assert_not_called()
        self.assertIn(user.username, out)  # skipped list mentions username

    def test_user_without_last_name_skipped(self):
        user = _make_user(last="")
        out, mocks = _run(users=[user])
        mocks["builder"].make_contributor.assert_not_called()
        self.assertIn(user.username, out)

    def test_user_with_both_names_not_skipped(self):
        user = _make_user(first="Alice", last="Smith")
        _, mocks = _run(users=[user])
        # Either matched or created — never skipped
        # (matched_tile=None → make_contributor called)
        mocks["builder"].make_contributor.assert_called_once()

    def test_found_users_count_in_output(self):
        users = [_make_user(username="u1"), _make_user(username="u2")]
        out, _ = _run(users=users)
        self.assertIn("2", out)


# ---------------------------------------------------------------------------
# Unmatched users (no existing contributor record)
# ---------------------------------------------------------------------------


class TestUnmatchedUsers(SimpleTestCase):

    def test_make_contributor_called_for_unmatched_user(self):
        user = _make_user()
        _, mocks = _run(users=[user], matched_tile=None)
        mocks["builder"].make_contributor.assert_called_once()

    def test_contributor_spec_receives_user_data(self):
        user = _make_user(
            first="Bob", last="Jones", email="bob@example.com", username="bjones"
        )
        _, mocks = _run(users=[user], matched_tile=None)
        spec_call_kwargs = mocks["spec_cls"].call_args.kwargs
        self.assertEqual(spec_call_kwargs.get("first_name"), "Bob")
        self.assertEqual(spec_call_kwargs.get("name"), "Jones")
        self.assertEqual(spec_call_kwargs.get("email"), "bob@example.com")
        self.assertEqual(spec_call_kwargs.get("bcap_username"), "bjones")

    def test_bulk_index_called_after_create(self):
        user = _make_user()
        _, mocks = _run(users=[user], matched_tile=None, dry_run=False)
        mocks["bulk_index"].assert_called_once()

    def test_created_contributor_in_output(self):
        user = _make_user(username="newuser")
        out, _ = _run(users=[user], matched_tile=None)
        self.assertIn("newuser", out)

    def test_dry_run_no_make_contributor(self):
        user = _make_user()
        _, mocks = _run(users=[user], matched_tile=None, dry_run=True)
        mocks["builder"].make_contributor.assert_not_called()


# ---------------------------------------------------------------------------
# Matched users (existing contributor tile found)
# ---------------------------------------------------------------------------


class TestMatchedUsers(SimpleTestCase):

    def test_set_bcap_username_called_when_no_existing_username(self):
        user = _make_user(username="asmith")
        tile = _make_tile(username_value=None)  # no existing username
        _, mocks = _run(users=[user], matched_tile=tile)
        mocks["svc"].set_bcap_username.assert_called_once_with("contrib-uuid", "asmith")

    def test_set_bcap_username_not_called_when_already_linked(self):
        user = _make_user(username="asmith")
        tile = _make_tile(username_value="asmith")  # already set
        _, mocks = _run(users=[user], matched_tile=tile)
        mocks["svc"].set_bcap_username.assert_not_called()

    def test_dry_run_does_not_call_set_bcap_username(self):
        user = _make_user(username="asmith")
        tile = _make_tile(username_value=None)
        _, mocks = _run(users=[user], matched_tile=tile, dry_run=True)
        mocks["svc"].set_bcap_username.assert_not_called()

    def test_matched_user_not_passed_to_make_contributor(self):
        user = _make_user()
        tile = _make_tile()
        _, mocks = _run(users=[user], matched_tile=tile)
        mocks["builder"].make_contributor.assert_not_called()

    def test_matched_contributor_id_in_output(self):
        user = _make_user(username="asmith")
        tile = _make_tile(contributor_id="known-uuid")
        out, _ = _run(users=[user], matched_tile=tile)
        self.assertIn("known-uuid", out)

    def test_already_linked_status_in_output(self):
        user = _make_user(username="asmith")
        tile = _make_tile(username_value="asmith")
        out, _ = _run(users=[user], matched_tile=tile)
        self.assertIn("already linked", out)


# ---------------------------------------------------------------------------
# Missing org (Archaeology Branch contributor not found)
# ---------------------------------------------------------------------------


class TestMissingOrg(SimpleTestCase):

    def test_missing_org_prints_warning(self):
        user = _make_user()
        out, _ = _run(users=[user], org_id=None)
        self.assertIn("not found", out.lower())

    def test_missing_org_does_not_raise(self):
        # Should complete without error even when org lookup returns None.
        user = _make_user()
        _run(users=[user], org_id=None)  # must not raise


# ---------------------------------------------------------------------------
# Empty user list
# ---------------------------------------------------------------------------


class TestEmptyUserList(SimpleTestCase):

    def test_no_users_no_bulk_index(self):
        _, mocks = _run(users=[])
        mocks["bulk_index"].assert_not_called()

    def test_no_users_no_make_contributor(self):
        _, mocks = _run(users=[])
        mocks["builder"].make_contributor.assert_not_called()

    def test_no_users_output_contains_zero_count(self):
        out, _ = _run(users=[])
        self.assertIn("0", out)

    def test_summary_sections_always_printed(self):
        out, _ = _run(users=[])
        self.assertIn("Matched", out)
        self.assertIn("Skipped", out)
