import uuid
from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest import mock

from django.test import TestCase

from bcap.services.contributor_service import (
    ContributorSummary,
    ContributorService,
    NewContributor,
)
from bcap.util.aliases.contributor import ContributorAliases
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.aliases.permit_application import (
    PermitApplicationAliases as pa,
    PermitApplicationGroupAliases as pa_groups,
)
from bcap.builders.contributor_builder import ContributorSpec
from bcap.util.controlled_list import reference_value
from tests.builders import FixtureBuilder

from tests.controlled_list_fixtures import ControlledListFixtures


def days_from_today(days):
    """An ISO date offset from today, for membership start/end bounds."""
    return (date.today() + timedelta(days=days)).isoformat()


# Wide windows so the UTC-vs-local boundary between the service's "today" and the
# test's never matters.
ACTIVE = {"start_date": days_from_today(-30), "end_date": days_from_today(30)}
EXPIRED = {"start_date": days_from_today(-60), "end_date": days_from_today(-30)}
FUTURE = {"start_date": days_from_today(30), "end_date": days_from_today(60)}


class ContributorServiceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ControlledListFixtures.seed()

    def setUp(self):
        super().setUp()
        self.builder = FixtureBuilder()
        self.contributor_type = reference_value("contributor", "contributor_type")
        self.service = ContributorService()

    def make(self, name, first_name=None, **kwargs):
        """Create a contributor; first_name=None makes an organization."""
        spec = ContributorSpec(self.contributor_type, first_name, name, **kwargs)
        return self.builder.make_contributor(spec)

    def make_with_orgs(self, name, memberships, first_name=None, bcap_username=None):
        """Create a contributor with one associated_organization tile per
        (organization, date-window) in ``memberships``."""
        builder = self.builder
        contributor = builder.new_resource("contributor")
        tile = builder.append_blank_tile_for_group(
            contributor,
            "contributor",
            {
                "first_name": builder.localized(first_name) if first_name else None,
                "contributor_name": builder.localized(name),
                "contributor_type": self.contributor_type,
                "bcap_username": bcap_username,
                "inactive": None,
            },
        )
        for org, window in memberships:
            builder.append_blank_tile_for_group(
                tile,
                "associated_organization",
                {"associated_organization": org, **window},
            )
        contributor.save(**builder.save_kwargs)
        return contributor

    def test_username_contributor_id(self):
        grace = self.make("Hopper", first_name="Grace", bcap_username="gh")
        self.make("Turing", first_name="Alan", bcap_username="at")
        self.assertEqual(self.service.username_contributor_id("gh"), str(grace.pk))
        self.assertIsNone(self.service.username_contributor_id("nobody"))

    def test_by_ids(self):
        grace = self.make("Hopper", first_name="Grace")
        acme = self.make("Acme Corp")  # org: no first name, so name only
        # Name-sorted, so Acme precedes Hopper.
        self.assertEqual(
            [
                (c.id, c.name)
                for c in self.service.by_ids([str(grace.pk), str(acme.pk)])
            ],
            [(str(acme.pk), "Acme Corp"), (str(grace.pk), "Hopper, Grace")],
        )
        self.assertEqual(self.service.by_ids([]), [])

    def test_by_ids_tolerates_a_missing_contributor_group(self):
        # A referenced Contributor whose contributor group tile is absent (so the
        # loaded tree's group is None) reads as a blank name rather than crashing.
        stub = self.builder.new_resource("contributor")
        stub.save(**self.builder.save_kwargs)
        contributors = self.service.by_ids([str(stub.pk)])
        self.assertEqual([(c.id, c.name) for c in contributors], [(str(stub.pk), "")])

    def test_company_is_the_viewer_and_their_orgs_active_members(self):
        # The viewer and the active members of their org are in; the org itself,
        # inactive, expired, future, and unrelated contributors are out.
        acme = self.make("Acme Corp")
        grace = self.make(
            "Hopper",
            first_name="Grace",
            bcap_username="gh",
            associated_organization=acme,
            **ACTIVE,
        )
        ada = self.make(
            "Lovelace", first_name="Ada", associated_organization=acme, **ACTIVE
        )
        self.make("Babbage", inactive=True, associated_organization=acme, **ACTIVE)
        self.make("Past Corp", associated_organization=acme, **EXPIRED)
        self.make("Future Corp", associated_organization=acme, **FUTURE)
        self.make("Turing", first_name="Alan", bcap_username="at")  # no org

        self.assertEqual(
            self.service.company_contributor_ids("gh"),
            {str(grace.pk), str(ada.pk)},
        )

    def test_company_membership_variants(self):
        # Open-ended membership (no dates) is active. An individual's company is
        # their org's members (here just themselves); an organization belongs to
        # no org, so its company is just itself; an unknown user gets nothing.
        acme = self.make("Acme Corp", bcap_username="acme")
        grace = self.make(
            "Hopper",
            first_name="Grace",
            bcap_username="gh",
            associated_organization=acme,
        )
        cases = {
            "individual viewer": ("gh", {str(grace.pk)}),
            "organization viewer": ("acme", {str(acme.pk)}),
            "unknown user": ("nobody", set()),
        }
        for label, (username, expected) in cases.items():
            with self.subTest(case=label):
                self.assertEqual(
                    self.service.company_contributor_ids(username), expected
                )

    def test_company_spans_every_org_the_viewer_belongs_to(self):
        # The viewer actively belongs to two orgs, so the company is the active
        # members of both (plus the viewer); an unrelated org's member is excluded.
        acme = self.make("Acme Corp")
        globex = self.make("Globex")
        grace = self.make_with_orgs(
            "Hopper",
            [(acme, ACTIVE), (globex, ACTIVE)],
            first_name="Grace",
            bcap_username="gh",
        )
        ada = self.make(
            "Lovelace", first_name="Ada", associated_organization=acme, **ACTIVE
        )
        bob = self.make(
            "Babbage", first_name="Bob", associated_organization=globex, **ACTIVE
        )
        other = self.make("Other Corp")
        self.make("Outsider", first_name="Out", associated_organization=other, **ACTIVE)

        self.assertEqual(
            self.service.company_contributor_ids("gh"),
            {str(grace.pk), str(ada.pk), str(bob.pk)},
        )

    def test_company_includes_half_open_memberships(self):
        acme = self.make("Acme Corp")
        viewer = self.make(
            "Hopper",
            first_name="Grace",
            bcap_username="gh",
            associated_organization=acme,
            **ACTIVE,
        )
        open_end = self.make(
            "Open End",
            first_name="Oe",
            associated_organization=acme,
            start_date=days_from_today(-30),
        )
        open_start = self.make(
            "Open Start",
            first_name="Os",
            associated_organization=acme,
            end_date=days_from_today(30),
        )
        self.assertEqual(
            self.service.company_contributor_ids("gh"),
            {str(viewer.pk), str(open_end.pk), str(open_start.pk)},
        )

    def test_company_membership_bounds_are_inclusive_of_today(self):
        frozen = datetime(2026, 6, 4, 12)

        def around(days):
            return (frozen.date() + timedelta(days=days)).isoformat()

        acme = self.make("Acme Corp")
        viewer = self.make(
            "Hopper",
            first_name="Grace",
            bcap_username="gh",
            associated_organization=acme,
            start_date=around(-30),
            end_date=around(30),
        )
        starts_today = self.make(
            "Starts Today",
            first_name="St",
            associated_organization=acme,
            start_date=around(0),
            end_date=around(30),
        )
        ends_today = self.make(
            "Ends Today",
            first_name="En",
            associated_organization=acme,
            start_date=around(-30),
            end_date=around(0),
        )
        with mock.patch(
            "bcap.services.contributor_service.timezone.now",
            return_value=frozen,
        ):
            result = self.service.company_contributor_ids("gh")
        self.assertEqual(
            result,
            {str(viewer.pk), str(starts_today.pk), str(ends_today.pk)},
        )

    def test_contributor_username(self):
        linked = self.make("Hopper", first_name="Grace", bcap_username="gh")
        unlinked = self.make("Turing", first_name="Alan")
        self.assertEqual(self.service.contributor_username(str(linked.pk)), "gh")
        self.assertIsNone(self.service.contributor_username(str(unlinked.pk)))
        self.assertIsNone(self.service.contributor_username(str(uuid.uuid4())))

    def test_company_usernames_are_the_members_logins(self):
        # Company members with a login contribute their username; a member
        # without one is simply absent (no empty entry).
        acme = self.make("Acme Corp")
        self.make(
            "Hopper",
            first_name="Grace",
            bcap_username="gh",
            associated_organization=acme,
            **ACTIVE,
        )
        self.make(
            "Lovelace",
            first_name="Ada",
            bcap_username="ada",
            associated_organization=acme,
            **ACTIVE,
        )
        self.make(  # active member, but no login
            "Babbage", first_name="Bob", associated_organization=acme, **ACTIVE
        )
        self.assertEqual(self.service.company_usernames("gh"), {"gh", "ada"})
        self.assertEqual(self.service.company_usernames("nobody"), set())

    def test_delete_contributor_removes_the_resource(self):
        contributor = self.make("Hopper", first_name="Grace")
        self.service.delete_contributor(str(contributor.pk))
        self.assertEqual(self.service.by_ids([str(contributor.pk)]), [])

    def test_is_invitable(self):
        # Only an existing, active, unlinked Contributor can be invited.
        invitable = self.make("Hopper", first_name="Grace")
        linked = self.make("Turing", first_name="Alan", bcap_username="at")
        inactive = self.make("Babbage", inactive=True)
        self.assertTrue(self.service.is_invitable(str(invitable.pk)))
        self.assertFalse(self.service.is_invitable(str(linked.pk)))
        self.assertFalse(self.service.is_invitable(str(inactive.pk)))
        self.assertFalse(self.service.is_invitable(str(uuid.uuid4())))

    def test_set_bcap_username_links_once(self):
        contributor = self.make("Hopper", first_name="Grace")
        self.assertTrue(self.service.set_bcap_username(str(contributor.pk), "gh"))
        self.assertEqual(
            self.service.username_contributor_id("gh"), str(contributor.pk)
        )
        # A second attempt is rejected and leaves the original binding intact.
        self.assertFalse(self.service.set_bcap_username(str(contributor.pk), "other"))
        self.assertEqual(
            self.service.username_contributor_id("gh"), str(contributor.pk)
        )
        self.assertIsNone(self.service.username_contributor_id("other"))

    def test_create_contributor_defaults_to_individual(self):
        # No contributor_type given, so it defaults to the Individual type.
        new_id = self.service.create_contributor(
            NewContributor(
                name="Hopper",
                first_name="Grace",
                email="grace@example.com",
            )
        )
        # Created unlinked, and reads back through the invite picker.
        self.assertTrue(self.service.is_invitable(new_id))
        self.assertEqual(
            self.service.invitable_contributors("Hopper"),
            [
                ContributorSummary(
                    id=new_id,
                    name="Hopper, Grace",
                    email="grace@example.com",
                    type="Individual",
                )
            ],
        )

    def test_create_contributor_stores_phone(self):
        new_id = self.service.create_contributor(
            NewContributor(
                name="Hopper",
                first_name="Grace",
                email="grace@example.com",
                phone="250-555-0100",
            )
        )
        resources = self.service._tiles(
            GraphSlugs.CONTRIBUTOR,
            [new_id],
            [ContributorAliases.CONTACT_PHONE_NUMBER],
        )
        data = resources[0].aliased_data.contributor.aliased_data
        self.assertEqual(data.contact_phone_number["display_value"], "250-555-0100")

    def test_invitable_contributors_filters_and_shapes(self):
        grace = self.make("Hopper", first_name="Grace")
        alan = self.make("Turing", first_name="Alan", bcap_username="at")  # linked
        babbage = self.make("Babbage", inactive=True)
        acme = self.make("Acme Corp")  # org: shown with name only
        by_id = {o.id: o for o in self.service.invitable_contributors()}
        self.assertIn(str(grace.pk), by_id)
        self.assertIn(str(acme.pk), by_id)
        self.assertNotIn(str(alan.pk), by_id)
        self.assertNotIn(str(babbage.pk), by_id)
        self.assertEqual(by_id[str(grace.pk)].name, "Hopper, Grace")
        self.assertEqual(by_id[str(acme.pk)].name, "Acme Corp")
        # Search narrows by name.
        self.assertEqual(
            [o.id for o in self.service.invitable_contributors("Hopper")],
            [str(grace.pk)],
        )


class LinkedContributorIdsTests(TestCase):
    """login_linked_contributor_ids keeps only active, login-linked contributors."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.contributors = ContributorService()
        builder = FixtureBuilder()
        ct = reference_value("contributor", "contributor_type")
        cls.linked = builder.make_contributor(
            ContributorSpec(ct, "Lee", "Linked", bcap_username="lee")
        )
        cls.unlinked = builder.make_contributor(ContributorSpec(ct, "Uma", "Unlinked"))
        cls.inactive = builder.make_contributor(
            ContributorSpec(ct, "Ivy", "Inactive", bcap_username="ivy", inactive=True)
        )

    def test_keeps_only_active_linked_contributors(self):
        ids = {str(c.pk) for c in (self.linked, self.unlinked, self.inactive)}
        self.assertEqual(
            self.contributors.login_linked_contributor_ids(ids),
            {str(self.linked.pk)},
        )

    def test_empty_input_returns_empty(self):
        self.assertEqual(self.contributors.login_linked_contributor_ids([]), set())


class ContributorsForResourceTests(TestCase):
    """ContributorService.contributors_for_resource returns the login-linked
    contributors referenced on a resource (ministry assignees included)."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = ContributorService()
        builder = FixtureBuilder()
        ct = reference_value("contributor", "contributor_type")

        # Referenced on the permit and login-linked: in via the linked source.
        cls.officer = builder.make_contributor(
            ContributorSpec(ct, "Ola", "Officer", bcap_username="ola")
        )
        # A ministry assignee, referenced on a nested process_module child:
        # in via the scan reaching nested tiles, not just the top-level group.
        cls.assignee = builder.make_contributor(
            ContributorSpec(ct, "Ash", "Assignee", bcap_username="ash")
        )
        # Login-linked but referenced nowhere on the permit: excluded.
        cls.bystander = builder.make_contributor(
            ContributorSpec(ct, "Bea", "Bystander", bcap_username="bea")
        )

        req = builder.make_process_requirement(
            {
                "id": "REQ-1",
                "name": "Review",
                "due": "2026-04-01",
                "notes": "",
                "satisfied": False,
                "sub_requirements": [],
            }
        )
        permit = builder.new_resource("permit_application")
        permit.append_tile("application_admin")
        admin = permit.aliased_data.application_admin
        admin.aliased_data.project_officer = cls.officer
        builder.prune_blank_tiles(admin, pa_groups.PROCESS_MODULE, pa.MODULE_NAME)
        module = builder.append_blank_tile_for_group(
            admin,
            pa_groups.PROCESS_MODULE,
            {
                pa.MODULE_NAME: builder.localized("Permit Review"),
                pa.MODULE_ID: str(uuid.uuid4()),
                pa.MODULE_ORDER: 1,
            },
        )
        builder.prune_blank_tiles(module, pa.PROCESS_REQUIREMENT)
        child = builder.append_blank_tile_for_group(
            module,
            pa.PROCESS_REQUIREMENT,
            {pa.PROCESS_REQUIREMENT: req, pa.PROCESS_REQUIREMENT_ORDER: 1},
        )
        child.aliased_data.ministry_assignee = cls.assignee
        permit.save(**builder.save_kwargs)
        cls.permit = permit
        cls.plain = builder.make_resource("permit_application")

    def _ids(self, resource):
        return {c.id for c in self.service.contributors_for_resource(str(resource.pk))}

    def test_unions_linked_referenced_with_ministry_assignees(self):
        self.assertEqual(
            self._ids(self.permit), {str(self.officer.pk), str(self.assignee.pk)}
        )

    def test_returns_contributors_sorted_by_name(self):
        rows = self.service.contributors_for_resource(str(self.permit.pk))
        self.assertEqual([r.name for r in rows], ["Assignee, Ash", "Officer, Ola"])

    def test_options_carry_type_and_email_fields(self):
        # type comes from the fixture's contributor_type; email is unset here, so
        # it defaults to "". Both are part of the picker contract.
        rows = self.service.contributors_for_resource(str(self.permit.pk))
        self.assertTrue(all(r.type for r in rows))
        self.assertTrue(all(r.email == "" for r in rows))

    def test_unassigned_resource_falls_back_to_archaeology_branch(self):
        # The branch Contributor is migration-seeded, so a resource with nobody
        # assigned still has someone to address.
        branch_id = self.service.archaeology_branch_id()
        self.assertIsNotNone(branch_id)
        rows = self.service.contributors_for_resource(str(self.plain.pk))
        self.assertEqual([r.id for r in rows], [branch_id])

    def test_assigned_resource_does_not_get_the_branch(self):
        self.assertNotIn(self.service.archaeology_branch_id(), self._ids(self.permit))
