from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest import mock

from django.test import TestCase

from bcap.services.dashboard.contributor_service import ContributorService
from bcap.util.dashboard.resource_builder import ContributorSpec, ResourceBuilder

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
        self.builder = ResourceBuilder()
        self.contributor_type = self.builder.reference_value(
            "contributor", "contributor_type"
        )
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

    def test_names_by_contributor_id(self):
        grace = self.make("Hopper", first_name="Grace")
        acme = self.make("Acme Corp")  # org: no first name, so name only
        self.assertEqual(
            self.service.names_by_contributor_id([str(grace.pk), str(acme.pk)]),
            {str(grace.pk): "Grace Hopper", str(acme.pk): "Acme Corp"},
        )
        self.assertEqual(self.service.names_by_contributor_id([]), {})

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
            "bcap.services.dashboard.contributor_service.timezone.now",
            return_value=frozen,
        ):
            result = self.service.company_contributor_ids("gh")
        self.assertEqual(
            result,
            {str(viewer.pk), str(starts_today.pk), str(ends_today.pk)},
        )
