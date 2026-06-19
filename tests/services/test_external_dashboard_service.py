from django.contrib.auth import get_user_model
from django.test import TestCase

from arches.app.models.models import ResourceInstance

from bcap.models.resource_draft import ResourceDraft
from bcap.services.dashboard.external_dashboard_service import (
    ExternalDashboardService,
)
from bcap.services.dashboard.dashboard_types import (
    DashboardFilter,
    ExternalDashboardStatus,
)
from bcap.util.dashboard.resource_builder import ContributorSpec, ResourceBuilder

from tests.controlled_list_fixtures import ControlledListFixtures

# Permit Application lifecycle state ids, keyed by name.
LIFECYCLE_STATE_IDS = {
    "Draft": "9375c9a7-dad2-4f14-a5c1-d7e329fdde4f",
    "Active": "f75bb034-36e3-4ab4-8167-f520cf0b4c58",
    "Retired": "d95d9c0e-0e2c-4450-93a3-d788b91abcc8",
}


def make_user(username):
    return get_user_model().objects.create_user(username=username, password="pass")


def build_external_permit(builder, name, owner, lifecycle="Active", hca_permit=None):
    """A permit_application owned by ``owner`` in the given lifecycle state, with
    an optional related HCA permit."""
    permit = builder.new_resource("permit_application")
    builder.append_blank_tile_for_group(
        permit,
        "application_identification",
        {
            "project_name": builder.localized(name),
            "application_id": builder.localized(name),
        },
    )
    builder.append_blank_tile_for_group(
        permit,
        "application_admin",
        {
            "application_priority_level": builder.reference_value(
                "permit_application", "application_priority_level"
            ),
            "application_submission_date": "2026-06-18",
        },
    )
    if hca_permit is not None:
        builder.append_blank_tile_for_group(
            permit,
            "related_permit",
            {"related_permit": hca_permit, "is_related_permit": True},
        )
    permit.save(**builder.save_kwargs)
    # The builder sets neither, so stamp them directly.
    ResourceInstance.objects.filter(pk=permit.pk).update(
        principaluser=owner,
        resource_instance_lifecycle_state_id=LIFECYCLE_STATE_IDS[lifecycle],
    )
    return permit


def build_hca_permit(builder, number, holder):
    permit = builder.new_resource("hca_permit")
    builder.append_blank_tile_for_group(
        permit,
        "permit_identification",
        {
            "permit_number": number,
            "permit_holder": [holder],
            "hca_permit_type": builder.reference_value(
                "hca_permit", "hca_permit_type", "Investigation"
            ),
        },
    )
    permit.save(**builder.save_kwargs)
    return permit


class ExternalDashboardServiceTests(TestCase):
    """get_cards() for each external scope (own applications, associated
    companies) plus the per-card field and status mappings."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = ExternalDashboardService()
        builder = ResourceBuilder()
        contributor_type = builder.reference_value("contributor", "contributor_type")

        # Grace (user "me") and Alan (user "colleague") both belong to Acme, so
        # the associated-companies scope spans both their applications.
        cls.me = make_user("me")
        cls.colleague = make_user("colleague")
        cls.outsider = make_user("outsider")

        acme = builder.make_contributor(
            ContributorSpec(contributor_type, None, "Acme Corp")
        )
        builder.make_contributor(
            ContributorSpec(
                contributor_type,
                "Grace",
                "Hopper",
                bcap_username="me",
                associated_organization=acme,
            )
        )
        builder.make_contributor(
            ContributorSpec(
                contributor_type,
                "Alan",
                "Turing",
                bcap_username="colleague",
                associated_organization=acme,
            )
        )

        hca = build_hca_permit(builder, "HCA-001", acme)
        cls.mine_active = build_external_permit(
            builder, "Mine Active", cls.me, "Active", hca_permit=hca
        )
        cls.mine_draft_state = build_external_permit(
            builder, "Mine Draft", cls.me, "Draft"
        )
        cls.colleagues = build_external_permit(
            builder, "Colleague App", cls.colleague, "Active"
        )
        cls.outsiders = build_external_permit(
            builder, "Outsider App", cls.outsider, "Active"
        )
        cls.hca_id = str(hca.pk)

    def test_created_by_me_returns_only_the_users_own_applications(self):
        page = self.service.get_cards(
            DashboardFilter(status=ExternalDashboardStatus.CREATED_BY_ME), self.me
        )

        self.assertEqual(page.count, 2)
        self.assertEqual(
            {card.id for card in page.results},
            {str(self.mine_active.pk), str(self.mine_draft_state.pk)},
        )

    def test_no_status_defaults_to_created_by_me(self):
        page = self.service.get_cards(DashboardFilter(), self.me)

        self.assertEqual(
            {card.id for card in page.results},
            {str(self.mine_active.pk), str(self.mine_draft_state.pk)},
        )

    def test_card_fields_map_from_the_permit_and_related_hca(self):
        page = self.service.get_cards(DashboardFilter(), self.me)

        card = next(c for c in page.results if c.id == str(self.mine_active.pk))
        self.assertFalse(card.is_draft)
        self.assertEqual(card.project_name, "Mine Active")
        self.assertRegex(card.application_number, r"^APP-\d+$")
        self.assertEqual(card.submission_date, "2026-06-18")
        self.assertEqual(card.created_by_name, "me")
        self.assertEqual(card.permit_id, self.hca_id)
        self.assertEqual(card.permit_number, "HCA-001")
        # Personal/internal fields are not on the external card at all.
        self.assertFalse(hasattr(card, "ministry_assignee_name"))
        self.assertFalse(hasattr(card, "project_officer"))

    def test_status_maps_from_lifecycle_state(self):
        page = self.service.get_cards(DashboardFilter(), self.me)
        status_by_id = {c.id: c.status for c in page.results}

        self.assertEqual(status_by_id[str(self.mine_active.pk)], "Permit Active")
        self.assertEqual(status_by_id[str(self.mine_draft_state.pk)], "Under Review")

    def test_retired_lifecycle_has_no_mapped_status(self):
        builder = ResourceBuilder()
        retired = build_external_permit(builder, "Retired App", self.me, "Retired")

        page = self.service.get_cards(DashboardFilter(), self.me)

        status_by_id = {c.id: c.status for c in page.results}
        self.assertEqual(status_by_id[str(retired.pk)], "")

    def test_associated_companies_scope_includes_colleagues_applications(self):
        page = self.service.get_cards(
            DashboardFilter(
                status=ExternalDashboardStatus.CREATED_BY_ASSOCIATED_COMPANIES
            ),
            self.me,
        )

        ids = {card.id for card in page.results}
        # Grace and Alan both belong to Acme, so the scope spans both their
        # applications; the outsider (no shared org) is excluded.
        self.assertIn(str(self.mine_active.pk), ids)
        self.assertIn(str(self.colleagues.pk), ids)
        self.assertNotIn(str(self.outsiders.pk), ids)

    def test_outsider_sees_only_their_own(self):
        page = self.service.get_cards(DashboardFilter(), self.outsider)

        self.assertEqual([card.id for card in page.results], [str(self.outsiders.pk)])

    def test_associated_companies_scope_empty_without_a_linked_contributor(self):
        # The outsider has no Contributor, so there are no company usernames to
        # scope by: the page is empty rather than erroring.
        page = self.service.get_cards(
            DashboardFilter(
                status=ExternalDashboardStatus.CREATED_BY_ASSOCIATED_COMPANIES
            ),
            self.outsider,
        )

        self.assertEqual(page.count, 0)
        self.assertEqual(page.results, [])


class ExternalDashboardDraftsTests(TestCase):
    """The DRAFTS scope reads ResourceDrafts, not saved resources."""

    @classmethod
    def setUpTestData(cls):
        cls.service = ExternalDashboardService()
        cls.user = make_user("drafter")
        cls.other = make_user("other")
        cls.draft = ResourceDraft.objects.create(
            user=cls.user,
            graph_slug="permit_application",
            data={
                "aliased_data": {
                    "application_identification": {
                        "aliased_data": {
                            "project_name": {"en": {"value": "Draft Project"}},
                            "application_id": {"en": {"value": "DRAFT-1"}},
                        }
                    }
                }
            },
        )
        # A draft for another graph and another user -- neither should surface.
        ResourceDraft.objects.create(user=cls.user, graph_slug="hca_permit")
        ResourceDraft.objects.create(user=cls.other, graph_slug="permit_application")

    def test_drafts_scope_returns_only_the_users_permit_application_drafts(self):
        page = self.service.get_cards(
            DashboardFilter(status=ExternalDashboardStatus.DRAFTS), self.user
        )

        self.assertEqual(page.count, 1)
        card = page.results[0]
        self.assertEqual(card.id, str(self.draft.id))
        self.assertTrue(card.is_draft)
        self.assertEqual(card.status, "Submission Required")
        self.assertEqual(card.project_name, "Draft Project")
        self.assertEqual(card.application_number, "DRAFT-1")
        self.assertEqual(card.created_by_name, "drafter")


class ExternalDashboardDraftRobustnessTests(TestCase):
    """Draft blobs are unvalidated, so the card builder must tolerate missing
    sections, missing fields, and malformed JSON without raising."""

    @classmethod
    def setUpTestData(cls):
        cls.service = ExternalDashboardService()
        cls.user = make_user("messy")

    def _draft_card(self, data):
        # One new draft per user/graph (unique constraint), so clear first.
        ResourceDraft.objects.filter(user=self.user).delete()
        ResourceDraft.objects.create(
            user=self.user, graph_slug="permit_application", data=data
        )
        page = self.service.get_cards(
            DashboardFilter(status=ExternalDashboardStatus.DRAFTS), self.user
        )
        self.assertEqual(page.count, 1)
        return page.results[0]

    def test_empty_data_yields_blank_identification(self):
        card = self._draft_card({})

        self.assertTrue(card.is_draft)
        self.assertEqual(card.status, "Submission Required")
        self.assertEqual(card.project_name, "")
        self.assertEqual(card.application_number, "")

    def test_partial_identification_fills_only_present_fields(self):
        card = self._draft_card(
            {
                "aliased_data": {
                    "application_identification": {
                        "aliased_data": {
                            "project_name": {"en": {"value": "Only Name"}},
                        }
                    }
                }
            }
        )

        self.assertEqual(card.project_name, "Only Name")
        self.assertEqual(card.application_number, "")

    def test_malformed_data_degrades_to_blank_without_raising(self):
        # A non-dict blob or wrong-typed section must not crash the dashboard.
        malformed = [
            [1, 2],
            "not-an-object",
            {"aliased_data": "not-a-dict"},
            {"aliased_data": {"application_identification": "not-a-dict"}},
            {"aliased_data": {"application_identification": {"aliased_data": []}}},
        ]
        for data in malformed:
            with self.subTest(data=data):
                card = self._draft_card(data)
                self.assertEqual(card.project_name, "")
                self.assertEqual(card.application_number, "")


class ExternalDashboardPaginationTests(TestCase):
    """limit/page slicing for the external dashboard."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = ExternalDashboardService()
        cls.user = make_user("pager")
        builder = ResourceBuilder()
        permits = [
            build_external_permit(builder, f"App {i}", cls.user, "Active")
            for i in range(3)
        ]
        cls.permit_ids = {str(p.pk) for p in permits}

    def test_limit_caps_page_size_but_not_count(self):
        page = self.service.get_cards(DashboardFilter(limit=2, page=1), self.user)

        self.assertEqual(page.count, 3)
        self.assertEqual(len(page.results), 2)

    def test_pages_partition_every_application_without_overlap(self):
        first = self.service.get_cards(DashboardFilter(limit=2, page=1), self.user)
        second = self.service.get_cards(DashboardFilter(limit=2, page=2), self.user)

        self.assertEqual(len(first.results), 2)
        self.assertEqual(len(second.results), 1)
        seen = {card.id for card in first.results + second.results}
        self.assertEqual(seen, self.permit_ids)
