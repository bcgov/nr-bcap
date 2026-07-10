from itertools import chain
from types import SimpleNamespace

from django.test import TestCase

from arches_querysets.models import TileTree

from bcap.services.dashboard.internal_dashboard_service import (
    InternalDashboardService,
)
from bcap.services.dashboard.dashboard_types import (
    DashboardFilter,
    InternalDashboardStatus,
)
from bcap.services.permit_application.permit_application_service import (
    PermitApplicationService,
)
from bcap.util.bcap_aliases import GraphSlugs
from bcap.builders.contributor_builder import ContributorSpec
from bcap.util.controlled_list import reference_value
from tests.builders import FixtureBuilder
from tests.services.test_bcap_message_service import make_message

from tests.controlled_list_fixtures import ControlledListFixtures


def build_permit_graph():
    """A minimal Permit Application graph for the dashboard tests: one permit
    linked to an HCA Permit (held by Acme Corp) and three process requirements
    -- satisfied "Review" (order 1), outstanding "Field Assessment" (order 2),
    and outstanding "Site Inspection" (order 3). The card surfaces the
    lowest-order outstanding requirement, "Field Assessment". Returns the
    created resources."""
    builder = FixtureBuilder()
    contributor_type = reference_value("contributor", "contributor_type")

    ada = builder.make_contributor(ContributorSpec(contributor_type, "Ada", "Lovelace"))
    acme = builder.make_contributor(
        ContributorSpec(contributor_type, None, "Acme Corp")
    )
    # Grace maps to the test user (bcap_username) and belongs to Acme, so she is
    # the ASSIGNED_TO_ME match and Acme is her ASSIGNED_TO_ASSOCIATED_COMPANIES.
    grace = builder.make_contributor(
        ContributorSpec(
            contributor_type,
            "Grace",
            "Hopper",
            bcap_username="testuser",
            associated_organization=acme,
        )
    )
    alan = builder.make_contributor(ContributorSpec(contributor_type, "Alan", "Turing"))

    hca_permit = builder.new_resource("hca_permit")
    builder.append_blank_tile_for_group(
        hca_permit,
        "permit_identification",
        {
            "permit_number": "HCA-001",
            "permit_holder": [acme],
            "hca_permit_type": reference_value(
                "hca_permit", "hca_permit_type", "Investigation"
            ),
        },
    )
    hca_permit.save(**builder.save_kwargs)

    review = builder.make_process_requirement(
        {
            "id": "REQ-1",
            "name": "Review",
            "due": "2026-01-02",
            "notes": "done",
            "satisfied": True,
            "sub_requirements": [
                {
                    "name": "Forms",
                    "sort_order": 1,
                    "description": "",
                    "sub_satisfied": True,
                },
            ],
        }
    )
    assessment = builder.make_process_requirement(
        {
            "id": "REQ-2",
            "name": "Field Assessment",
            "due": "2026-02-15",
            "notes": "awaiting site access",
            "satisfied": False,
            "sub_requirements": [
                {
                    "name": "Forms",
                    "sort_order": 1,
                    "description": "",
                    "sub_satisfied": False,
                },
                {
                    "name": "Inspection",
                    "sort_order": 2,
                    "description": "",
                    "sub_satisfied": True,
                },
            ],
        }
    )
    site = builder.make_process_requirement(
        {
            "id": "REQ-3",
            "name": "Site Inspection",
            "due": "2026-04-01",
            "notes": "not started",
            "satisfied": False,
            "sub_requirements": [],
        }
    )

    permit = builder.new_resource("permit_application")
    builder.append_blank_tile_for_group(
        permit,
        "application_identification",
        {
            "project_name": builder.localized("My Project"),
            "application_id": builder.localized("APP-1"),
        },
    )
    builder.append_blank_tile_for_group(
        permit,
        "related_permit",
        {"related_permit": hca_permit, "is_related_permit": True},
    )
    permit.append_tile("application_admin")
    admin = permit.aliased_data.application_admin
    admin.aliased_data.project_officer = alan
    admin.aliased_data.application_submission_date = "2026-01-01"
    # One application_admin child per (requirement, assignee, order). "Site
    # Inspection" (order 3) precedes "Field Assessment" (order 2) in tile order,
    # so the card only surfaces the right row by lowest order, not position.
    children = [
        (review, ada, 1),
        (site, ada, 3),
        (assessment, grace, 2),
    ]
    for i, (requirement, assignee, order) in enumerate(children):
        if i > 0:
            admin.append_tile("process_requirement")
        child = admin.aliased_data.process_requirement[i]
        child.aliased_data.process_requirement_order = order
        child.aliased_data.process_requirement = requirement
        child.aliased_data.ministry_assignee = assignee
    permit.save(**builder.save_kwargs)

    return SimpleNamespace(
        permit=permit,
        hca_permit=hca_permit,
        ada=ada,
        grace=grace,
        acme=acme,
        alan=alan,
        review=review,
        assessment=assessment,
        site=site,
    )


def build_minimal_permit(builder, name):
    """A permit_application with only the tiles a card needs (identification,
    admin priority, and one outstanding requirement so it isn't hidden), so
    pagination tests can cheaply create several visible permits. Returns the
    created resource."""
    requirement = builder.make_process_requirement(
        {
            "id": f"REQ-{name}",
            "name": "Outstanding",
            "due": "2026-03-01",
            "notes": "",
            "satisfied": False,
            "sub_requirements": [],
        }
    )
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
            "application_priority_level": reference_value(
                "permit_application", "application_priority_level"
            ),
            "application_submission_date": "2026-01-01",
        },
    )
    child = permit.aliased_data.application_admin.aliased_data.process_requirement[0]
    child.aliased_data.process_requirement_order = 1
    child.aliased_data.process_requirement = requirement
    permit.save(**builder.save_kwargs)
    return permit


def build_permit_with_investigation(builder, name, host_graph=GraphSlugs.INVESTIGATION):
    """A dashboard-visible permit whose outstanding requirement's
    submission_data points at an Investigation host -- the linkage the
    unread-message roll-up follows. Returns the permit and the host resource."""
    host = builder.make_resource(host_graph)
    requirement = builder.make_process_requirement(
        {
            "id": f"REQ-{name}",
            "name": "Outstanding",
            "due": "2026-03-01",
            "notes": "",
            "satisfied": False,
            "sub_requirements": [],
        }
    )
    builder.link_submission(str(requirement.pk), host)
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
            "application_priority_level": reference_value(
                "permit_application", "application_priority_level"
            ),
            "application_submission_date": "2026-01-01",
        },
    )
    child = permit.aliased_data.application_admin.aliased_data.process_requirement[0]
    child.aliased_data.process_requirement_order = 1
    child.aliased_data.process_requirement = requirement
    permit.save(**builder.save_kwargs)
    return permit, host


def build_all_satisfied_permit(builder, name):
    """A permit_application whose only process requirement is satisfied, so the
    card has none to surface. Returns the created resource."""
    requirement = builder.make_process_requirement(
        {
            "id": "REQ-DONE",
            "name": "Review",
            "due": "2026-01-02",
            "notes": "done",
            "satisfied": True,
            "sub_requirements": [],
        }
    )
    permit = builder.new_resource("permit_application")
    builder.append_blank_tile_for_group(
        permit,
        "application_identification",
        {
            "project_name": builder.localized(name),
            "application_id": builder.localized(name),
        },
    )
    permit.append_tile("application_admin")
    child = permit.aliased_data.application_admin.aliased_data.process_requirement[0]
    child.aliased_data.process_requirement_order = 1
    child.aliased_data.process_requirement = requirement
    admin = permit.aliased_data.application_admin
    admin.aliased_data.application_submission_date = "2026-01-01"
    permit.save(**builder.save_kwargs)
    return permit


def build_unassigned_permit(builder, name):
    """A permit_application whose active (unsatisfied) requirement has no
    ministry_assignee. Returns the created resource."""
    requirement = builder.make_process_requirement(
        {
            "id": "REQ-UNASSIGNED",
            "name": "Needs Owner",
            "due": "2026-03-01",
            "notes": "nobody assigned",
            "satisfied": False,
            "sub_requirements": [],
        }
    )
    permit = builder.new_resource("permit_application")
    builder.append_blank_tile_for_group(
        permit,
        "application_identification",
        {
            "project_name": builder.localized(name),
            "application_id": builder.localized(name),
        },
    )
    permit.append_tile("application_admin")
    child = permit.aliased_data.application_admin.aliased_data.process_requirement[0]
    child.aliased_data.process_requirement_order = 1
    child.aliased_data.process_requirement = requirement
    admin = permit.aliased_data.application_admin
    admin.aliased_data.application_submission_date = "2026-01-01"
    permit.save(**builder.save_kwargs)
    return permit


def build_blank_requirement_permit(builder, name):
    """A permit_application whose application_admin holds only the blank
    process_requirement child auto-created with the group -- no requirement
    assigned (the shape an externally-created application has before any
    requirement is added). It has nothing actionable, so the dashboard must hide
    it rather than surface a card with no requirement. Returns the resource."""
    permit = builder.new_resource("permit_application")
    builder.append_blank_tile_for_group(
        permit,
        "application_identification",
        {
            "project_name": builder.localized(name),
            "application_id": builder.localized(name),
        },
    )
    permit.append_tile("application_admin")
    admin = permit.aliased_data.application_admin
    admin.aliased_data.application_submission_date = "2026-01-01"
    permit.save(**builder.save_kwargs)
    return permit


def build_groupless_requirement_permit(builder, name):
    """A permit whose active requirement is a process_requirement with no group
    tiles at all -- unsatisfied (no status), so the card surfaces it. Returns
    the permit and the requirement id."""
    requirement = builder.new_resource("process_requirement")
    requirement.save(**builder.save_kwargs)
    permit = builder.new_resource("permit_application")
    builder.append_blank_tile_for_group(
        permit,
        "application_identification",
        {
            "project_name": builder.localized(name),
            "application_id": builder.localized(name),
        },
    )
    permit.append_tile("application_admin")
    child = permit.aliased_data.application_admin.aliased_data.process_requirement[0]
    child.aliased_data.process_requirement_order = 1
    child.aliased_data.process_requirement = requirement
    admin = permit.aliased_data.application_admin
    admin.aliased_data.application_submission_date = "2026-01-01"
    permit.save(**builder.save_kwargs)
    return permit, str(requirement.pk)


def build_unsubmitted_permit(builder, name):
    """A permit with an actionable requirement but no submission date -- a draft
    the dashboard hides until it is submitted. Returns the created resource."""
    requirement = builder.make_process_requirement(
        {
            "id": f"REQ-{name}",
            "name": "Outstanding",
            "due": "2026-03-01",
            "notes": "",
            "satisfied": False,
            "sub_requirements": [],
        }
    )
    permit = builder.new_resource("permit_application")
    builder.append_blank_tile_for_group(
        permit,
        "application_identification",
        {
            "project_name": builder.localized(name),
            "application_id": builder.localized(name),
        },
    )
    permit.append_tile("application_admin")
    child = permit.aliased_data.application_admin.aliased_data.process_requirement[0]
    child.aliased_data.process_requirement_order = 1
    child.aliased_data.process_requirement = requirement
    # deliberately no application_submission_date
    permit.save(**builder.save_kwargs)
    return permit


def _tile(**leaves):
    """A TileTree wrapping the given alias -> representation-value leaves, so
    _application_core's traversal descends into it like a real group tile."""
    return TileTree(aliased_data=SimpleNamespace(**leaves))


class _DashboardServiceData:
    """Builds the test graph once per class and exposes the resources' ids as
    strings -- the form the service returns -- so the assertions stay readable."""

    @classmethod
    def setUpTestData(cls):
        # Seeded resources are rolled back with the class transaction.
        ControlledListFixtures.seed()
        cls.service = InternalDashboardService()
        graph = build_permit_graph()

        cls.permit_id = str(graph.permit.pk)
        cls.hca_permit_id = str(graph.hca_permit.pk)
        cls.ada_id = str(graph.ada.pk)
        cls.grace_id = str(graph.grace.pk)
        cls.acme_id = str(graph.acme.pk)
        cls.alan_id = str(graph.alan.pk)
        cls.review_id = str(graph.review.pk)
        cls.assessment_id = str(graph.assessment.pk)
        cls.site_id = str(graph.site.pk)


class DashboardServiceTests(_DashboardServiceData, TestCase):
    """The dashboard service against the shared permit graph: the public
    get_cards() API end to end, plus the individual steps it chains together.
    Both share one graph build (setUpTestData runs once per class)."""

    def test_get_cards_builds_one_card_from_the_permit_graph(self):
        page = self.service.get_cards(DashboardFilter())

        self.assertEqual(page.count, 1)
        self.assertEqual(len(page.results), 1)
        card = page.results[0]
        self.assertEqual(card.id, self.permit_id)
        self.assertEqual(card.project_name, "My Project")
        self.assertRegex(card.application_number, r"^APP-\d+$")
        # "Review" is satisfied, so the card surfaces "Field Assessment".
        self.assertEqual(card.requirement_name, "Field Assessment")
        self.assertEqual(card.requirement_due_date, "2026-02-15")
        self.assertEqual(card.assessment_notes, "awaiting site access")
        self.assertEqual(card.requirement_id, self.assessment_id)
        self.assertEqual(card.permit_number, "HCA-001")
        self.assertEqual(card.permit_id, self.hca_permit_id)
        self.assertEqual(card.permit_holder, "Acme Corp")
        self.assertEqual(card.permit_holder_ids, [self.acme_id])
        # The project_officer on the permit's application_admin group.
        self.assertEqual(card.project_officer, "Alan Turing")
        self.assertEqual(card.project_officer_id, self.alan_id)
        # The assignee on the chosen ("Field Assessment") tile.
        self.assertEqual(card.ministry_assignee_name, "Grace Hopper")
        self.assertEqual(card.ministry_assignee_id, self.grace_id)

    def test_assigned_to_me_status_filters_by_user_bcap_username(self):
        # Grace's bcap_username is "testuser" and she is the assignee of the
        # active ("Field Assessment") requirement, so ASSIGNED_TO_ME returns the
        # permit for that user.
        matching = self.service.get_cards(
            DashboardFilter(status=InternalDashboardStatus.ASSIGNED_TO_ME), "testuser"
        )
        self.assertEqual(matching.count, 1)
        self.assertEqual([card.id for card in matching.results], [self.permit_id])

        # A user with no matching Contributor (bcap_username) matches nothing.
        none = self.service.get_cards(
            DashboardFilter(status=InternalDashboardStatus.ASSIGNED_TO_ME), "nobody"
        )
        self.assertEqual(none.count, 0)
        self.assertEqual(none.results, [])

    def test_blank_username_assignment_filters_require_a_user(self):
        # ASSIGNED_TO_ME is keyed on the viewer's Contributor, so a blank
        # username is rejected rather than matching every permit.
        for username in (None, ""):
            with self.subTest(username=username):
                with self.assertRaises(ValueError):
                    self.service.get_cards(
                        DashboardFilter(status=InternalDashboardStatus.ASSIGNED_TO_ME),
                        username,
                    )

    def test_unassigned_status_returns_only_permits_with_no_active_assignee(self):
        # The graph permit's active requirement ("Field Assessment") is assigned
        # to Grace, so it is excluded; add a permit whose active requirement has
        # no assignee, which is the only UNASSIGNED match.
        unassigned_id = str(build_unassigned_permit(FixtureBuilder(), "Orphan").pk)

        page = self.service.get_cards(
            DashboardFilter(status=InternalDashboardStatus.UNASSIGNED)
        )

        self.assertEqual([card.id for card in page.results], [unassigned_id])

    def test_no_status_returns_all_actionable_permits_regardless_of_assignee(self):
        # No status means the assignment filter is not applied: both the
        # assigned graph permit and an unassigned one are returned.
        unassigned_id = str(build_unassigned_permit(FixtureBuilder(), "Orphan").pk)

        page = self.service.get_cards(DashboardFilter())

        self.assertEqual(
            {card.id for card in page.results}, {self.permit_id, unassigned_id}
        )

    def test_permits_returns_count_and_the_permit_application(self):
        count, permits = self.service._permits(DashboardFilter())

        self.assertEqual(count, 1)
        self.assertEqual(len(permits), 1)
        self.assertEqual(str(permits[0].pk), self.permit_id)

    def test_requirement_tiles_by_permit_groups_by_permit(self):
        _, permits = self.service._permits(DashboardFilter())

        by_permit = self.service._requirement_tiles_by_permit(permits)

        # The permit's three process-requirement tiles are grouped under its id.
        self.assertEqual(list(by_permit), [self.permit_id])
        self.assertEqual(len(by_permit[self.permit_id]), 3)

    def test_choose_requirements_picks_lowest_order_unsatisfied(self):
        _, permits = self.service._permits(DashboardFilter())
        by_permit = self.service._requirement_tiles_by_permit(permits)
        ids = self.service._referenced_ids(
            chain.from_iterable(by_permit.values()), self.service.PA.PROCESS_REQUIREMENT
        )

        chosen = self.service._choose_requirements(by_permit, ids)

        # "Review" (order 1) is satisfied; of the outstanding rows the card
        # surfaces "Field Assessment" (order 2) over "Site Inspection" (order 3).
        requirement = chosen[self.permit_id]
        self.assertEqual(
            (
                requirement.name,
                requirement.due_date,
                requirement.route,
                requirement.notes,
            ),
            (
                "Field Assessment",
                "2026-02-15",
                self.assessment_id,
                "awaiting site access",
            ),
        )
        # The chosen requirement carries its process_requirement tile.
        self.assertIsNotNone(requirement.tile)

    def test_hca_permits_maps_number_and_holders(self):
        _, permits = self.service._permits(DashboardFilter())

        hca_permits = self.service._hca_permits(permits)

        self.assertEqual(list(hca_permits), [self.hca_permit_id])
        hca = hca_permits[self.hca_permit_id]
        self.assertEqual(hca.number, "HCA-001")
        self.assertEqual(hca.holder_ids, [self.acme_id])

    def test_hca_permits_tolerates_a_missing_identification_group(self):
        # An HCA Permit whose permit_identification group tile is absent reads as
        # a blank number and no holders rather than crashing on the missing group.
        builder = FixtureBuilder()
        hca = builder.new_resource("hca_permit")
        hca.save(**builder.save_kwargs)
        permit = builder.new_resource("permit_application")
        builder.append_blank_tile_for_group(
            permit,
            "related_permit",
            {"related_permit": hca, "is_related_permit": True},
        )
        permit.save(**builder.save_kwargs)
        permits = self.service._resources(
            GraphSlugs.PERMIT_APPLICATION, [permit.pk], [self.service.PA.RELATED_PERMIT]
        )

        hca_permits = self.service._hca_permits(permits)

        result = hca_permits[str(hca.pk)]
        self.assertEqual(result.number, "")
        self.assertEqual(result.holder_ids, [])

    def test_choose_requirements_reads_a_requirement_with_missing_groups(self):
        # A requirement with no group tiles is unsatisfied, so it is surfaced;
        # its absent groups must read as blank fields rather than crash.
        permit, requirement_id = build_groupless_requirement_permit(
            FixtureBuilder(), "Bare"
        )
        permit_id = str(permit.pk)

        _, permits = self.service._permits(DashboardFilter())
        by_permit = self.service._requirement_tiles_by_permit(permits)
        ids = self.service._referenced_ids(
            chain.from_iterable(by_permit.values()), self.service.PA.PROCESS_REQUIREMENT
        )
        chosen = self.service._choose_requirements(by_permit, ids)

        requirement = chosen[permit_id]
        self.assertEqual(requirement.route, requirement_id)
        self.assertEqual(
            (requirement.name, requirement.due_date, requirement.notes),
            ("", "", ""),
        )

    def test_contributor_names_resolves_assignees_and_holders(self):
        _, permits = self.service._permits(DashboardFilter())
        by_permit = self.service._requirement_tiles_by_permit(permits)
        hca_permits = self.service._hca_permits(permits)
        assignee_ids = self.service._referenced_ids(
            chain.from_iterable(by_permit.values()), self.service.PA.MINISTRY_ASSIGNEE
        )

        names = self.service._contributor_names(assignee_ids, hca_permits)

        self.assertEqual(
            names,
            {
                self.ada_id: "Ada Lovelace",
                self.grace_id: "Grace Hopper",
                self.acme_id: "Acme Corp",
            },
        )

    def test_node_value_tolerates_a_none_aliased_data(self):
        self.assertEqual(self.service._node_value(None, "requirement_name"), {})

    def test_application_core_handles_missing_groups_and_null_values(self):
        aliased = SimpleNamespace(
            application_identification=_tile(
                project_name={"display_value": "My Project"},
                # Present node, null display_value -- not the same as absent.
                application_id={"display_value": None},
            ),
            # application_admin group has no tile.
            application_admin=None,
            # An unset resource-instance node represents as [], not a dict.
            related_permit=[],
        )

        core = self.service._application_core(aliased)

        self.assertEqual(core.project_name, "My Project")
        # A missing group yields no leaf, so its fields fall back to "".
        self.assertEqual(core.industrial_sector, "")
        self.assertEqual(core.priority_level, "")
        self.assertEqual(core.application_number, "")
        self.assertIsNone(core.related_permit_id)

    def test_application_core_with_all_groups_none(self):
        aliased = SimpleNamespace(
            application_identification=None,
            application_admin=None,
            related_permit=None,
        )

        core = self.service._application_core(aliased)

        self.assertEqual(
            (
                core.project_name,
                core.application_number,
                core.industrial_sector,
                core.priority_level,
                core.related_permit_id,
            ),
            ("", "", "", "", None),
        )


class DashboardServicePaginationTests(TestCase):
    """limit/page slicing, against several permits so paging is observable."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        builder = FixtureBuilder()
        # Three bare permits are enough to observe limit capping and paging.
        permits = [build_minimal_permit(builder, f"Permit {i}") for i in range(3)]
        cls.permit_ids = {str(p.pk) for p in permits}
        cls.service = InternalDashboardService()

    def test_limit_caps_page_size_but_not_count(self):
        page = self.service.get_cards(DashboardFilter(limit=2, page=1))

        self.assertEqual(page.count, 3)
        self.assertEqual(page.limit, 2)
        self.assertEqual(page.page, 1)
        self.assertEqual(len(page.results), 2)

    def test_pages_partition_every_permit_without_overlap(self):
        first = self.service.get_cards(DashboardFilter(limit=2, page=1))
        second = self.service.get_cards(DashboardFilter(limit=2, page=2))

        self.assertEqual(len(first.results), 2)
        self.assertEqual(len(second.results), 1)
        seen = {card.id for card in first.results + second.results}
        self.assertEqual(seen, self.permit_ids)

    def test_page_past_the_end_is_empty_but_count_holds(self):
        page = self.service.get_cards(DashboardFilter(limit=2, page=99))

        self.assertEqual(page.count, 3)
        self.assertEqual(page.results, [])


class DashboardServiceNoPermitsTests(TestCase):
    """get_cards() with no Permit Application resources in the database. This
    case builds no graph, so the permit query comes back empty."""

    def test_get_cards_returns_empty_page(self):
        page = InternalDashboardService().get_cards(DashboardFilter())
        self.assertEqual(page.count, 0)
        self.assertEqual(page.results, [])


class DashboardServiceAllSatisfiedTests(TestCase):
    """A permit whose requirements are all satisfied has nothing actionable, so
    it is hidden from the dashboard entirely."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        builder = FixtureBuilder()
        cls.permit_id = str(build_all_satisfied_permit(builder, "Done").pk)
        cls.service = InternalDashboardService()

    def test_all_satisfied_permit_is_hidden(self):
        page = self.service.get_cards(DashboardFilter())

        self.assertEqual(page.count, 0)
        self.assertEqual(page.results, [])


class DashboardServiceBlankRequirementTests(TestCase):
    """A permit whose only process_requirement tile is blank (no requirement
    assigned) has nothing the card could surface, so the dashboard hides it.
    Guards against the active-requirement filter and _choose_requirements
    diverging: an included permit with no choosable requirement would build a
    card from None."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        builder = FixtureBuilder()
        cls.permit_id = str(build_blank_requirement_permit(builder, "Blank").pk)
        cls.service = InternalDashboardService()

    def test_permit_with_only_a_blank_requirement_tile_is_hidden(self):
        page = self.service.get_cards(DashboardFilter())

        self.assertEqual(page.count, 0)
        self.assertEqual(page.results, [])


class DashboardServiceSubmissionDateTests(TestCase):
    """Only submitted applications reach the internal dashboard: a permit with
    an actionable requirement but no submission date is a draft and is hidden,
    while an otherwise-identical submitted permit appears."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        builder = FixtureBuilder()
        cls.submitted_id = str(build_minimal_permit(builder, "Submitted").pk)
        cls.draft_id = str(build_unsubmitted_permit(builder, "Draft").pk)
        cls.service = InternalDashboardService()

    def test_only_the_submitted_permit_appears(self):
        page = self.service.get_cards(DashboardFilter())

        self.assertEqual(page.count, 1)
        self.assertEqual([card.id for card in page.results], [self.submitted_id])


class DashboardUnreadRollupTests(TestCase):
    """The unread-message roll-up: a permit's card count spans messages on the
    permit and on the host resources its process requirements' submission_data
    points at (its related investigation/alteration/inspection)."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = InternalDashboardService()
        builder = FixtureBuilder()
        cls.permit, cls.host = build_permit_with_investigation(builder, "Roll")
        cls.permit_id = str(cls.permit.pk)
        cls.host_id = str(cls.host.pk)

    def test_context_ids_include_the_permit_and_its_submission_host(self):
        contexts = PermitApplicationService().submission_context_ids_for_permits(
            [self.permit]
        )
        self.assertEqual(contexts, {self.permit_id: {self.permit_id, self.host_id}})

    def test_a_permit_with_no_submission_maps_to_only_itself(self):
        bare = build_minimal_permit(FixtureBuilder(), "Bare")
        contexts = PermitApplicationService().submission_context_ids_for_permits([bare])
        self.assertEqual(contexts, {str(bare.pk): {str(bare.pk)}})

    def test_card_count_rolls_up_messages_on_the_permit_and_the_host(self):
        builder = FixtureBuilder()
        contributor_type = reference_value("contributor", "contributor_type")
        reader = builder.make_contributor(
            ContributorSpec(contributor_type, "Ray", "Reader", bcap_username="roller")
        )
        # One unread on the permit, one on its submission host, and one already
        # read that must not count.
        make_message(builder, context=self.permit, recipient=reader, subject="p")
        make_message(builder, context=self.host, recipient=reader, subject="h")
        make_message(
            builder,
            context=self.host,
            recipient=reader,
            read_date="2026-02-01",
            subject="read",
        )

        page = self.service.get_cards(DashboardFilter(), "roller")

        card = next(c for c in page.results if c.id == self.permit_id)
        self.assertEqual(card.unread_messages, 2)
