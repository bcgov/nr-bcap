from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from arches.app.models.models import ResourceInstance

from bcap.services.workflow_draft_service import WorkflowDraftService
from bcap.util.bcap_aliases import GraphSlugs
from bcap.services.dashboard.external_dashboard_service import (
    ExternalDashboardService,
)
from bcap.services.dashboard.dashboard_types import (
    DashboardFilter,
    ExternalDashboardStatus,
)
from bcap.builders.contributor_builder import ContributorSpec
from bcap.util.aliases.permit_application import (
    PermitApplicationAliases as pa,
    PermitApplicationGroupAliases as pa_groups,
)
from bcap.util.controlled_list import reference_value
from tests.builders import FixtureBuilder

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
            # Pinned by label so the card's submission_type is assertable.
            "filing_type": reference_value(
                "permit_application", "filing_type", "Site Visit"
            ),
        },
    )
    builder.append_blank_tile_for_group(
        permit,
        "application_admin",
        {
            "application_priority_level": reference_value(
                "permit_application", "application_priority_level"
            ),
            "application_submission_date": "2026-06-18",
        },
    )
    # External permits carry no modules; drop the blank one append_tile creates.
    builder.prune_blank_tiles(
        permit.aliased_data.application_admin,
        pa_groups.PROCESS_MODULE,
        pa.MODULE_NAME,
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
            "hca_permit_type": reference_value(
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
        builder = FixtureBuilder()
        contributor_type = reference_value("contributor", "contributor_type")

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
        builder = FixtureBuilder()
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
        ControlledListFixtures.seed()
        cls.service = ExternalDashboardService()
        cls.user = make_user("drafter")
        cls.other = make_user("other")
        cls.permit = build_external_permit(
            FixtureBuilder(), "Parent Project", cls.user, "Active"
        )
        cls.draft = WorkflowDraftService().create(
            cls.user,
            "permit_application",
            {
                "application_identification": {
                    "aliased_data": {
                        "project_name": {"en": {"value": "Draft Project"}},
                        "application_id": {"en": {"value": "DRAFT-1"}},
                    }
                }
            },
        )
        cls.investigation_draft = WorkflowDraftService().create(
            cls.user,
            GraphSlugs.INVESTIGATION,
            {},
            parent_resource_id=str(cls.permit.pk),
        )
        # Another user's draft, which must not surface.
        WorkflowDraftService().create(cls.other, "permit_application", {})

    def test_drafts_scope_returns_only_the_users_drafts(self):
        page = self.service.get_cards(
            DashboardFilter(status=ExternalDashboardStatus.DRAFTS), self.user
        )

        self.assertEqual(page.count, 2)
        card = next(c for c in page.results if c.id == str(self.draft.id))
        self.assertTrue(card.is_draft)
        self.assertEqual(card.graph_slug, GraphSlugs.PERMIT_APPLICATION)
        self.assertEqual(card.status, "Submission Required")
        self.assertEqual(card.project_name, "Draft Project")
        self.assertEqual(card.application_number, "DRAFT-1")
        self.assertEqual(card.created_by_name, "drafter")

    def test_module_drafts_get_a_card_carrying_their_graph(self):
        page = self.service.get_cards(
            DashboardFilter(status=ExternalDashboardStatus.DRAFTS), self.user
        )

        card = next(c for c in page.results if c.id == str(self.investigation_draft.id))
        self.assertTrue(card.is_draft)
        self.assertEqual(card.graph_slug, GraphSlugs.INVESTIGATION)

    def test_module_draft_is_named_by_the_permit_it_was_started_from(self):
        page = self.service.get_cards(
            DashboardFilter(status=ExternalDashboardStatus.DRAFTS), self.user
        )

        card = next(c for c in page.results if c.id == str(self.investigation_draft.id))
        self.assertEqual(card.permit_application_id, str(self.permit.pk))
        self.assertEqual(card.project_name, "Parent Project")
        self.assertRegex(card.application_number, r"^APP-\d+$")
        self.assertEqual(card.submission_type, "Site Visit")

    def test_internal_staff_see_every_draft_but_the_card_names_the_requester(self):
        # Draft visibility widened to all internal users, so staff get the
        # applicant's draft back. Pins current behaviour: created_by_name is
        # stamped from the requester, so it reads as staff's own draft.
        staff = make_user("branch-staff")
        staff.groups.add(Group.objects.get(name="Resource Editor"))

        page = self.service.get_cards(
            DashboardFilter(status=ExternalDashboardStatus.DRAFTS), staff
        )

        card = next(c for c in page.results if c.id == str(self.draft.id))
        self.assertEqual(card.created_by_name, "branch-staff")

    def test_a_drafts_own_identification_wins_over_its_parents(self):
        page = self.service.get_cards(
            DashboardFilter(status=ExternalDashboardStatus.DRAFTS), self.user
        )

        card = next(c for c in page.results if c.id == str(self.draft.id))
        self.assertEqual(card.project_name, "Draft Project")
        self.assertEqual(card.permit_application_id, "")


class ExternalDashboardDraftRobustnessTests(TestCase):
    """Draft blobs are unvalidated, so the card builder must tolerate missing
    sections, missing fields, and malformed JSON without raising."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = ExternalDashboardService()
        cls.user = make_user("messy")
        cls.parent = build_external_permit(
            FixtureBuilder(), "Parent Project", cls.user, "Active"
        )

    def _draft_card(self, data, parent_resource_id=""):
        # The dashboard expects one draft, so clear the user's drafts first.
        ResourceInstance.objects.filter(
            graph__slug=GraphSlugs.WORKFLOW_DRAFTS, principaluser=self.user
        ).delete()
        WorkflowDraftService().create(
            self.user,
            "permit_application",
            data,
            parent_resource_id=parent_resource_id,
        )
        page = self.service.get_cards(
            DashboardFilter(status=ExternalDashboardStatus.DRAFTS), self.user
        )
        self.assertEqual(page.count, 1)
        return page.results[0]

    @staticmethod
    def _identification(**values):
        return {
            "application_identification": {
                "aliased_data": {
                    alias: {"en": {"value": value}} for alias, value in values.items()
                }
            }
        }

    def test_empty_data_yields_blank_identification(self):
        card = self._draft_card({})

        self.assertTrue(card.is_draft)
        self.assertEqual(card.status, "Submission Required")
        self.assertEqual(card.project_name, "")
        self.assertEqual(card.application_number, "")

    def test_partial_identification_fills_only_present_fields(self):
        card = self._draft_card(
            {
                "application_identification": {
                    "aliased_data": {
                        "project_name": {"en": {"value": "Only Name"}},
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
            {"application_identification": "not-a-dict"},
            {"application_identification": {"aliased_data": []}},
        ]
        for data in malformed:
            with self.subTest(data=data):
                card = self._draft_card(data)
                self.assertEqual(card.project_name, "")
                self.assertEqual(card.application_number, "")

    def test_a_pre_move_blob_shape_degrades_to_blank(self):
        # The group keys moved to the blob's top level; a draft saved under the
        # old nested shape must read as blank rather than raise.
        card = self._draft_card(
            {"aliased_data": self._identification(project_name="Old Shape")}
        )

        self.assertEqual(card.project_name, "")
        self.assertEqual(card.application_number, "")

    def test_the_drafts_own_value_wins_over_the_parents(self):
        card = self._draft_card(
            self._identification(project_name="Draft Name"),
            parent_resource_id=str(self.parent.pk),
        )

        self.assertEqual(card.project_name, "Draft Name")
        # Fields the draft doesn't carry still come from the parent.
        self.assertEqual(card.submission_type, "Site Visit")

    def test_a_blank_draft_value_falls_back_to_the_parent(self):
        card = self._draft_card(
            self._identification(project_name=""),
            parent_resource_id=str(self.parent.pk),
        )

        self.assertEqual(card.project_name, "Parent Project")

    def test_a_deleted_parent_leaves_blanks_but_keeps_the_permit_id(self):
        gone = build_external_permit(FixtureBuilder(), "Doomed", self.user, "Active")
        parent_id = str(gone.pk)
        ResourceInstance.objects.filter(pk=parent_id).delete()

        card = self._draft_card({}, parent_resource_id=parent_id)

        self.assertEqual(card.permit_application_id, parent_id)
        self.assertEqual(card.project_name, "")
        self.assertEqual(card.application_number, "")


class ExternalDashboardPaginationTests(TestCase):
    """limit/page slicing for the external dashboard."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = ExternalDashboardService()
        cls.user = make_user("pager")
        builder = FixtureBuilder()
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
