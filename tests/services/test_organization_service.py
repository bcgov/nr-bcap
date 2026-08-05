"""Company visibility: who belongs to an organization today, which
organization a new resource is stamped for, and which rows that makes visible."""

from datetime import datetime, timedelta
from unittest import mock

from django.test import TestCase

from bcap.services.contributor.organization_service import OrganizationService

from tests.controlled_list_fixtures import ControlledListFixtures
from tests.services.contributor_fixtures import (
    ACTIVE,
    EXPIRED,
    FUTURE,
    ContributorFixtureMixin,
    days_from_today,
)


class OrganizationServiceTest(ContributorFixtureMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ControlledListFixtures.seed()

    def setUp(self):
        super().setUp()
        self.service = OrganizationService()

    def test_only_memberships_in_force_today_count(self):
        # An expired or not-yet-started membership is not one you belong to now.
        acme = self.make("Acme Corp")
        past = self.make("Past Corp")
        future = self.make("Future Corp")
        self.make_with_orgs(
            "Hopper",
            [(acme, ACTIVE), (past, EXPIRED), (future, FUTURE)],
            first_name="Grace",
            bcap_username="gh",
        )

        self.assertEqual(self.service.organization_ids("gh"), {str(acme.pk)})

    def test_membership_variants(self):
        # Open-ended membership (no dates) is active; an organization belongs to
        # no org of its own; an unknown user belongs to nothing.
        acme = self.make("Acme Corp", bcap_username="acme")
        self.make(
            "Hopper",
            first_name="Grace",
            bcap_username="gh",
            associated_organization=acme,
        )
        cases = {
            "individual viewer": ("gh", {str(acme.pk)}),
            "organization viewer": ("acme", set()),
            "unknown user": ("nobody", set()),
        }
        for label, (username, expected) in cases.items():
            with self.subTest(case=label):
                self.assertEqual(self.service.organization_ids(username), expected)

    def test_spans_every_org_the_viewer_belongs_to(self):
        acme = self.make("Acme Corp")
        globex = self.make("Globex")
        self.make("Other Corp")
        self.make_with_orgs(
            "Hopper",
            [(acme, ACTIVE), (globex, ACTIVE)],
            first_name="Grace",
            bcap_username="gh",
        )

        self.assertEqual(
            self.service.organization_ids("gh"), {str(acme.pk), str(globex.pk)}
        )

    def test_half_open_memberships_count(self):
        # One bound left unset means open in that direction, not excluded.
        open_end = self.make("Open End Corp")
        open_start = self.make("Open Start Corp")
        self.make_with_orgs(
            "Hopper",
            [
                (open_end, {"start_date": days_from_today(-30)}),
                (open_start, {"end_date": days_from_today(30)}),
            ],
            first_name="Grace",
            bcap_username="gh",
        )

        self.assertEqual(
            self.service.organization_ids("gh"),
            {str(open_end.pk), str(open_start.pk)},
        )

    def test_membership_bounds_are_inclusive_of_today(self):
        frozen = datetime(2026, 6, 4, 12)

        def around(days):
            return (frozen.date() + timedelta(days=days)).isoformat()

        starts_today = self.make("Starts Today Corp")
        ends_today = self.make("Ends Today Corp")
        ended_yesterday = self.make("Ended Yesterday Corp")
        self.make_with_orgs(
            "Hopper",
            [
                (starts_today, {"start_date": around(0), "end_date": around(30)}),
                (ends_today, {"start_date": around(-30), "end_date": around(0)}),
                (ended_yesterday, {"start_date": around(-30), "end_date": around(-1)}),
            ],
            first_name="Grace",
            bcap_username="gh",
        )

        with mock.patch(
            "bcap.services.contributor.organization_service.timezone.now",
            return_value=frozen,
        ):
            result = self.service.organization_ids("gh")

        self.assertEqual(result, {str(starts_today.pk), str(ends_today.pk)})
