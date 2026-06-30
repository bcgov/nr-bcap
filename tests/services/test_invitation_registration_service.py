import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.utils import timezone

from bcap.models import RegistrationLink
from bcap.services.dashboard.contributor_service import (
    ContributorService,
    NewContributor,
)
from bcap.services.registration.invitation_registration_service import (
    PENDING_REGISTRATION_SESSION_KEY,
    InvitationRegistrationService,
)
from bcap.builders.contributor_builder import ContributorSpec
from bcap.util.controlled_list import reference_value
from tests.builders import FixtureBuilder

from tests.controlled_list_fixtures import ControlledListFixtures


class InvitationRegistrationServiceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ControlledListFixtures.seed()

    def setUp(self):
        super().setUp()
        self.builder = FixtureBuilder()
        self.contributor_type = reference_value("contributor", "contributor_type")
        self.contributors = ContributorService()
        self.service = InvitationRegistrationService(self.contributors)
        self.user = get_user_model().objects.create_user(
            username="idir\\jdoe", email="jdoe@example.com"
        )
        # Default group granted on redemption when no groups are specified.
        Group.objects.get_or_create(name="Guest")

    def make_contributor(self, name="Hopper", first_name="Grace", **kwargs):
        spec = ContributorSpec(self.contributor_type, first_name, name, **kwargs)
        return self.builder.make_contributor(spec)

    def new_contributor(self):
        return NewContributor(
            name="Hopper",
            contributor_type=self.contributor_type[0],
            first_name="Grace",
            email="grace@example.com",
        )

    def test_issue_link_for_existing_contributor(self):
        contributor = self.make_contributor()
        link = self.service.issue_link(self.user, contributor_id=str(contributor.pk))
        self.assertEqual(str(link.contributor_id), str(contributor.pk))
        self.assertIsNone(link.new_contributor)
        self.assertIsNone(link.used)
        self.assertGreater(link.expires, timezone.now())

    def test_issue_link_for_new_contributor_defers_creation(self):
        link = self.service.issue_link(
            self.user, new_contributor=self.new_contributor()
        )
        self.assertIsNone(link.contributor_id)
        self.assertEqual(link.new_contributor["email"], "grace@example.com")
        # The Contributor resource does not exist until the link is redeemed.
        self.assertEqual(self.contributors.invitable_contributors("Hopper"), [])

    def test_redeem_existing_binds_username_and_grants_groups(self):
        contributor = self.make_contributor()
        link = self.service.issue_link(self.user, contributor_id=str(contributor.pk))
        redeemed = self.service.redeem_link(link.id, self.user)
        self.assertEqual(redeemed.id, link.id)
        self.assertEqual(
            self.contributors.username_contributor_id(self.user.username),
            str(contributor.pk),
        )
        self.assertTrue(self.user.groups.filter(name="Guest").exists())
        link.refresh_from_db()
        self.assertIsNotNone(link.used)
        self.assertEqual(link.used_by_id, self.user.pk)

    def test_redeem_grants_the_links_selected_groups(self):
        Group.objects.get_or_create(name="Permit Reviewer")
        contributor = self.make_contributor()
        link = self.service.issue_link(
            self.user,
            contributor_id=str(contributor.pk),
            groups=["Permit Reviewer"],
        )
        self.service.redeem_link(link.id, self.user)
        self.assertTrue(self.user.groups.filter(name="Permit Reviewer").exists())
        # The settings default is not also applied when groups are chosen.
        self.assertFalse(self.user.groups.filter(name="Guest").exists())

    def test_redeem_drops_non_whitelisted_groups_and_falls_back(self):
        Group.objects.get_or_create(name="Resource Editor")
        contributor = self.make_contributor()
        link = self.service.issue_link(
            self.user,
            contributor_id=str(contributor.pk),
            groups=["Resource Editor"],  # not in SELF_MANAGE_ROLE_GROUPS
        )
        self.service.redeem_link(link.id, self.user)
        self.assertFalse(self.user.groups.filter(name="Resource Editor").exists())
        # Nothing whitelisted remained, so the default is granted.
        self.assertTrue(self.user.groups.filter(name="Guest").exists())

    def test_redeem_new_contributor_creates_then_binds(self):
        link = self.service.issue_link(
            self.user, new_contributor=self.new_contributor()
        )
        redeemed = self.service.redeem_link(link.id, self.user)
        self.assertIsNotNone(redeemed)
        new_id = self.contributors.username_contributor_id(self.user.username)
        self.assertIsNotNone(new_id)
        link.refresh_from_db()
        self.assertEqual(str(link.contributor_id), new_id)

    def test_redeem_rolls_back_created_contributor_on_failure(self):
        link = self.service.issue_link(
            self.user, new_contributor=self.new_contributor()
        )
        with mock.patch.object(
            self.contributors, "set_bcap_username", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(RuntimeError):
                self.service.redeem_link(link.id, self.user)
        # The Contributor created mid-redemption was rolled back, so none lingers.
        self.assertEqual(self.contributors.invitable_contributors("Hopper"), [])

    def test_redeem_missing_token_returns_none(self):
        self.assertIsNone(self.service.redeem_link(uuid.uuid4(), self.user))

    def test_redeem_expired_or_used_returns_none(self):
        contributor = self.make_contributor()
        expired = RegistrationLink.objects.create(
            contributor_id=contributor.pk,
            created_by=self.user,
            expires=timezone.now() - timedelta(days=1),
        )
        used = RegistrationLink.objects.create(
            contributor_id=contributor.pk,
            created_by=self.user,
            expires=timezone.now() + timedelta(days=1),
            used=timezone.now(),
        )
        self.assertIsNone(self.service.redeem_link(expired.id, self.user))
        self.assertIsNone(self.service.redeem_link(used.id, self.user))

    def test_redeem_already_linked_contributor_returns_none(self):
        contributor = self.make_contributor(bcap_username="someone_else")
        link = self.service.issue_link(self.user, contributor_id=str(contributor.pk))
        self.assertIsNone(self.service.redeem_link(link.id, self.user))
        self.assertFalse(self.user.groups.filter(name="Guest").exists())
        link.refresh_from_db()
        self.assertIsNone(link.used)

    def test_redeem_blocked_when_user_already_holds_a_contributor(self):
        # One user maps to at most one Contributor.
        self.make_contributor(name="Existing", bcap_username=self.user.username)
        other = self.make_contributor(name="Other")
        link = self.service.issue_link(self.user, contributor_id=str(other.pk))
        self.assertIsNone(self.service.redeem_link(link.id, self.user))
        # Second Contributor stays unlinked, link unused, no groups granted.
        self.assertTrue(self.contributors.is_invitable(str(other.pk)))
        self.assertFalse(self.user.groups.filter(name="Guest").exists())
        link.refresh_from_db()
        self.assertIsNone(link.used)

    def test_redeem_new_contributor_blocked_leaves_no_orphan(self):
        # The guard runs before the Contributor is created, so a rejected
        # new-contributor redemption creates nothing.
        self.make_contributor(name="Existing", bcap_username=self.user.username)
        link = self.service.issue_link(
            self.user, new_contributor=self.new_contributor()
        )
        self.assertIsNone(self.service.redeem_link(link.id, self.user))
        self.assertEqual(self.contributors.invitable_contributors("Hopper"), [])

    def idir_request(self, **session):
        return SimpleNamespace(
            user=self.user,
            session={
                "oauth_token": {"userinfo": {"loginSource": "IDIR"}},
                **session,
            },
        )

    def test_redeem_pending_redeems_token_stashed_in_session(self):
        contributor = self.make_contributor()
        link = self.service.issue_link(self.user, contributor_id=str(contributor.pk))
        request = self.idir_request(**{PENDING_REGISTRATION_SESSION_KEY: str(link.id)})
        self.service.redeem_pending(request)
        self.assertNotIn(PENDING_REGISTRATION_SESSION_KEY, request.session)
        self.assertEqual(
            self.contributors.username_contributor_id(self.user.username),
            str(contributor.pk),
        )

    def test_redeem_pending_redeems_for_bceid(self):
        contributor = self.make_contributor()
        link = self.service.issue_link(self.user, contributor_id=str(contributor.pk))
        request = SimpleNamespace(
            user=self.user,
            session={
                "oauth_token": {"userinfo": {"loginSource": "BCEID"}},
                PENDING_REGISTRATION_SESSION_KEY: str(link.id),
            },
        )
        self.service.redeem_pending(request)
        self.assertNotIn(PENDING_REGISTRATION_SESSION_KEY, request.session)
        self.assertEqual(
            self.contributors.username_contributor_id(self.user.username),
            str(contributor.pk),
        )

    def test_redeem_pending_without_pending_token_is_a_noop(self):
        self.service.redeem_pending(self.idir_request())
        self.assertFalse(self.user.groups.filter(name="Guest").exists())

    def redeemable_link(self):
        return RegistrationLink.objects.create(
            created_by=self.user, expires=timezone.now() + timedelta(days=1)
        )

    def test_ensure_invited_user_creates_account_for_invited_idir(self):
        token = {
            "userinfo": {
                "loginSource": "IDIR",
                "preferred_username": "idir\\newperson",
                "given_name": "New",
                "family_name": "Person",
            }
        }
        session = {PENDING_REGISTRATION_SESSION_KEY: str(self.redeemable_link().id)}
        request = SimpleNamespace(session=session)
        self.service.ensure_invited_user(request, token)
        created = User.objects.get(username="newperson@idir")
        self.assertEqual((created.first_name, created.last_name), ("New", "Person"))

    def test_ensure_invited_user_ignores_a_bogus_token(self):
        # A planted/invalid token must not provision an account; otherwise
        # invite-only access could be bypassed by anyone with a BC gov login.
        token = {
            "userinfo": {
                "loginSource": "IDIR",
                "preferred_username": "idir\\gatecrasher",
                "given_name": "Gate",
                "family_name": "Crasher",
            }
        }
        request = SimpleNamespace(
            session={PENDING_REGISTRATION_SESSION_KEY: "not-a-real-token"}
        )
        self.service.ensure_invited_user(request, token)
        self.assertFalse(User.objects.filter(username="gatecrasher@idir").exists())

    def test_ensure_invited_user_does_nothing_without_an_invite(self):
        token = {
            "userinfo": {
                "loginSource": "IDIR",
                "preferred_username": "idir\\uninvited",
            }
        }
        self.service.ensure_invited_user(SimpleNamespace(session={}), token)
        self.assertFalse(User.objects.filter(username="uninvited@idir").exists())

    def test_ensure_invited_user_creates_account_for_invited_bceid(self):
        # BCEID logins carry no family_name; last name lands blank.
        token = {
            "userinfo": {
                "loginSource": "BCEID",
                "preferred_username": "bceid\\newbiz",
                "given_name": "New",
            }
        }
        session = {PENDING_REGISTRATION_SESSION_KEY: str(self.redeemable_link().id)}
        request = SimpleNamespace(session=session)
        self.service.ensure_invited_user(request, token)
        created = User.objects.get(username="newbiz@bceid")
        self.assertEqual((created.first_name, created.last_name), ("New", ""))

    def test_ensure_invited_user_does_not_gate_on_login_source(self):
        # A redeemable invite is the authorization; the login source is not
        # checked, so any signed-in invitee gets their account.
        token = {
            "userinfo": {
                "preferred_username": "someone@example",
                "given_name": "Some",
                "family_name": "One",
            }
        }
        session = {PENDING_REGISTRATION_SESSION_KEY: str(self.redeemable_link().id)}
        request = SimpleNamespace(session=session)
        self.service.ensure_invited_user(request, token)
        self.assertTrue(User.objects.filter(username="someone@example").exists())
