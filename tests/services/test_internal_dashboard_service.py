from itertools import chain
from types import SimpleNamespace
from uuid import uuid4

from django.test import TestCase

from arches.app.models.resource import Resource

from arches_querysets.models import TileTree

from bcap.services.dashboard.internal_dashboard_service import (
    InternalDashboardService,
)
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.services.dashboard.dashboard_types import (
    DashboardFilter,
    InternalDashboardStatus,
)
from bcap.services.bcap_service_request.bcap_service_request_service import (
    BcapServiceRequestService,
)
from bcap.util.aliases.bcap_service_request import BcapServiceRequestAliases as sr
from bcap.util.bcap_aliases import GraphSlugs
from tests.builders import FixtureBuilder
from tests.services.contributor_fixtures import make_contributor, make_party
from tests.permit_fixtures import (
    RequirementRow,
    build_service_request,
    make_requirement,
)
from tests.services.message_fixtures import make_message

from tests.controlled_list_fixtures import ControlledListFixtures


def build_sr_graph():
    """A minimal BCAP Service Request graph for the dashboard tests: one SR
    with three process requirements -- satisfied "Review" (order 1), outstanding
    "Field Assessment" (order 2), and outstanding "Site Inspection" (order 3).
    The card surfaces the lowest-order outstanding requirement, "Field Assessment".
    Returns the created resources."""
    builder = FixtureBuilder()

    ada = make_contributor(builder, "Lovelace", "Ada")
    acme = make_contributor(builder, "Acme Corp")
    # Grace maps to the test user (bcap_username) and belongs to Acme, so she is
    # the ASSIGNED_TO_ME match and Acme is her ASSIGNED_TO_ASSOCIATED_COMPANIES.
    grace = make_contributor(
        builder,
        "Hopper",
        "Grace",
        bcap_username="testuser",
        associated_organization=acme,
    )

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

    # One process_requirement per (requirement, order, assignee), all under a
    # single module. "Site Inspection" (order 3) precedes "Field Assessment"
    # (order 2) in tile order, so the card surfaces the right row by lowest
    # order, not position.
    service_request = build_service_request(
        builder,
        "My Project",
        [
            RequirementRow(review, 1, ada),
            RequirementRow(site, 3, ada),
            RequirementRow(assessment, 2, grace),
        ],
        # Pinned by label so the card's submission_type is assertable.
        service_request_type="Submit a Site Visit",
    )

    return SimpleNamespace(
        service_request=service_request,
        ada=ada,
        grace=grace,
        acme=acme,
        review=review,
        assessment=assessment,
        site=site,
    )


def build_minimal_sr(builder, name, satisfied=False, submitted=True):
    """A bcap_service_request with only the tiles a card needs: identification,
    admin, and one process requirement under a single module. Unsatisfied and
    submitted, it is the cheapest SR the dashboard shows."""
    return build_service_request(
        builder,
        name,
        [RequirementRow(make_requirement(builder, name, satisfied))],
        submission_date="2026-01-01" if submitted else None,
    )


def build_sr_with_investigation(builder, name):
    """A dashboard-visible SR whose outstanding requirement's submission_data
    points at an Investigation host -- the linkage the unresolved-thread
    roll-up follows. Returns the SR, the host resource, and the requirement."""
    host = builder.make_resource(GraphSlugs.INVESTIGATION)
    requirement = make_requirement(builder, name)
    builder.link(str(requirement.pk), submission=host)
    service_request = build_service_request(
        builder, name, [RequirementRow(requirement)]
    )
    return service_request, host, requirement


def build_groupless_sr_requirement(builder, name):
    """An SR whose active requirement is a process_requirement with no group
    tiles at all -- unsatisfied (no status), so the card surfaces it. Returns
    the SR and the requirement id."""
    requirement = builder.new_resource("process_requirement")
    requirement.save(**builder.save_kwargs)
    service_request = build_service_request(
        builder, name, [RequirementRow(requirement)]
    )
    return service_request, str(requirement.pk)


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
        graph = build_sr_graph()

        cls.permit_id = str(graph.service_request.pk)
        cls.ada_id = str(graph.ada.pk)
        cls.grace_id = str(graph.grace.pk)
        cls.acme_id = str(graph.acme.pk)
        cls.review_id = str(graph.review.pk)
        cls.assessment_id = str(graph.assessment.pk)
        cls.site_id = str(graph.site.pk)


class DashboardServiceTests(_DashboardServiceData, TestCase):
    """The dashboard service against the shared SR graph: the public
    get_cards() API end to end, plus the individual steps it chains together.
    Both share one graph build (setUpTestData runs once per class)."""

    def test_get_cards_builds_one_card_from_the_sr_graph(self):
        page = self.service.get_cards(DashboardFilter())

        self.assertEqual(page.count, 1)
        self.assertEqual(len(page.results), 1)
        card = page.results[0]
        self.assertEqual(card.id, self.permit_id)
        self.assertEqual(card.project_name, "My Project")
        self.assertRegex(card.application_number, r"^[A-Z]+-\d{4}-\d+$")
        # "Review" is satisfied, so the card surfaces "Field Assessment".
        self.assertEqual(card.requirement_name, "Field Assessment")
        self.assertEqual(card.requirement_due_date, "2026-02-15")
        self.assertEqual(card.assessment_notes, "awaiting site access")
        self.assertEqual(card.requirement_id, self.assessment_id)
        # The assignee on the chosen ("Field Assessment") tile.
        self.assertEqual(card.ministry_assignee_name, "Hopper, Grace")
        self.assertEqual(card.ministry_assignee_id, self.grace_id)

    def test_assigned_to_me_status_filters_by_user_bcap_username(self):
        # Grace's bcap_username is "testuser" and she is the assignee of the
        # active ("Field Assessment") requirement, so ASSIGNED_TO_ME returns the
        # SR for that user.
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
        # username is rejected rather than matching every SR.
        for username in (None, ""):
            with self.subTest(username=username):
                with self.assertRaises(ValueError):
                    self.service.get_cards(
                        DashboardFilter(status=InternalDashboardStatus.ASSIGNED_TO_ME),
                        username,
                    )

    def test_unassigned_status_returns_only_srs_with_no_active_assignee(self):
        # The graph SR's active requirement ("Field Assessment") is assigned
        # to Grace, so it is excluded; add an SR whose active requirement has
        # no assignee, which is the only UNASSIGNED match.
        unassigned_id = str(build_minimal_sr(FixtureBuilder(), "Orphan").pk)

        page = self.service.get_cards(
            DashboardFilter(status=InternalDashboardStatus.UNASSIGNED)
        )

        self.assertEqual([card.id for card in page.results], [unassigned_id])

    def test_no_status_returns_all_actionable_srs_regardless_of_assignee(self):
        # No status means the assignment filter is not applied: both the
        # assigned graph SR and an unassigned one are returned.
        unassigned_id = str(build_minimal_sr(FixtureBuilder(), "Orphan").pk)

        page = self.service.get_cards(DashboardFilter())

        self.assertEqual(
            {card.id for card in page.results}, {self.permit_id, unassigned_id}
        )

    def test_permits_returns_count_and_the_sr(self):
        count, permits = self.service._permits(DashboardFilter())

        self.assertEqual(count, 1)
        self.assertEqual(len(permits), 1)
        self.assertEqual(str(permits[0].pk), self.permit_id)

    def test_requirement_tiles_by_permit_groups_by_sr(self):
        _, permits = self.service._permits(DashboardFilter())

        by_permit = self.service._requirement_tiles_by_permit(permits)

        # The SR's three process-requirement tiles are grouped under its id.
        self.assertEqual(list(by_permit), [self.permit_id])
        self.assertEqual(len(by_permit[self.permit_id]), 3)

    def test_choose_requirements_picks_lowest_order_unsatisfied(self):
        _, permits = self.service._permits(DashboardFilter())
        by_permit = self.service._requirement_tiles_by_permit(permits)
        ids = self.service._referenced_ids(
            chain.from_iterable(by_permit.values()), self.service.SR.PROCESS_REQUIREMENT
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
        permits = self.service._tiles(
            GraphSlugs.PERMIT_APPLICATION, [permit.pk], [self.service.PA.RELATED_PERMIT]
        )

        hca_permits = self.service._hca_permits(permits)

        result = hca_permits[str(hca.pk)]
        self.assertEqual(result.number, "")
        self.assertEqual(result.holder_ids, [])

    def test_choose_requirements_reads_a_requirement_with_missing_groups(self):
        # A requirement with no group tiles is unsatisfied, so it is surfaced;
        # its absent groups must read as blank fields rather than crash.
        service_request, requirement_id = build_groupless_sr_requirement(
            FixtureBuilder(), "Bare"
        )
        sr_id = str(service_request.pk)

        _, permits = self.service._permits(DashboardFilter())
        by_permit = self.service._requirement_tiles_by_permit(permits)
        ids = self.service._referenced_ids(
            chain.from_iterable(by_permit.values()), self.service.SR.PROCESS_REQUIREMENT
        )
        chosen = self.service._choose_requirements(by_permit, ids)

        requirement = chosen[sr_id]
        self.assertEqual(requirement.route, requirement_id)
        self.assertEqual(
            (requirement.name, requirement.due_date, requirement.notes),
            ("", "", ""),
        )

    def test_contributor_names_resolves_assignees(self):
        _, permits = self.service._permits(DashboardFilter())
        by_permit = self.service._requirement_tiles_by_permit(permits)
        assignee_ids = self.service._referenced_ids(
            chain.from_iterable(by_permit.values()), self.service.SR.MINISTRY_ASSIGNEE
        )

        names = self.service._contributor_names(assignee_ids, {})

        self.assertEqual(
            names,
            {
                self.ada_id: "Lovelace, Ada",
                self.grace_id: "Hopper, Grace",
            },
        )

    def test_node_value_tolerates_a_none_aliased_data(self):
        self.assertEqual(self.service.node_value(None, "requirement_name"), {})

    def test_order_value_treats_a_null_order_as_last(self):
        # A present-but-unset order node has node_value None. It must sort last
        # (inf) like a missing node, not return None, or the tuple sort in
        # _requirement_tiles_by_permit compares an int against None and crashes.
        self.assertEqual(self.service._order_value(None), float("inf"))
        self.assertEqual(self.service._order_value({"node_value": None}), float("inf"))
        self.assertEqual(self.service._order_value({"node_value": 2}), 2)

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
        self.assertEqual(core.organization, "")
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
                core.submission_type,
                core.industrial_sector,
                core.priority_level,
                core.organization,
                core.related_permit_id,
            ),
            ("", "", "", "", "", "", None),
        )


class DashboardServicePaginationTests(TestCase):
    """limit/page slicing, against several SRs so paging is observable."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        builder = FixtureBuilder()
        # Three bare SRs are enough to observe limit capping and paging.
        srs = [build_minimal_sr(builder, f"SR {i}") for i in range(3)]
        cls.sr_ids = {str(s.pk) for s in srs}
        cls.service = InternalDashboardService()

    def test_limit_caps_page_size_but_not_count(self):
        page = self.service.get_cards(DashboardFilter(limit=2, page=1))

        self.assertEqual(page.count, 3)
        self.assertEqual(page.limit, 2)
        self.assertEqual(page.page, 1)
        self.assertEqual(len(page.results), 2)

    def test_pages_partition_every_sr_without_overlap(self):
        first = self.service.get_cards(DashboardFilter(limit=2, page=1))
        second = self.service.get_cards(DashboardFilter(limit=2, page=2))

        self.assertEqual(len(first.results), 2)
        self.assertEqual(len(second.results), 1)
        seen = {card.id for card in first.results + second.results}
        self.assertEqual(seen, self.sr_ids)

    def test_page_past_the_end_is_empty_but_count_holds(self):
        page = self.service.get_cards(DashboardFilter(limit=2, page=99))

        self.assertEqual(page.count, 3)
        self.assertEqual(page.results, [])


class DashboardServiceNoSRsTests(TestCase):
    """get_cards() with no BCAP Service Request resources in the database."""

    def test_get_cards_returns_empty_page(self):
        page = InternalDashboardService().get_cards(DashboardFilter())
        self.assertEqual(page.count, 0)
        self.assertEqual(page.results, [])


class DashboardServiceVisibilityTests(TestCase):
    """Which SRs reach the dashboard, against one build of every shape that
    must not: unsubmitted (still a draft), all requirements satisfied (nothing
    actionable), and a blank process_requirement tile (nothing a card could
    surface, which would otherwise build a card from None)."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        builder = FixtureBuilder()
        cls.submitted_id = str(build_minimal_sr(builder, "Submitted").pk)
        build_minimal_sr(builder, "Draft", submitted=False)
        build_minimal_sr(builder, "Done", satisfied=True)
        build_service_request(builder, "Blank", [RequirementRow()])
        cls.service = InternalDashboardService()

    def test_only_the_submitted_actionable_sr_appears(self):
        page = self.service.get_cards(DashboardFilter())

        self.assertEqual(page.count, 1)
        self.assertEqual([card.id for card in page.results], [self.submitted_id])


class RequirementsByIdTests(TestCase):
    """_requirements_by_id reads the four card fields straight off the tiles'
    JSON, seeding a blank Requirement per id so one with no tiles still counts
    as unsatisfied."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = InternalDashboardService()
        builder = FixtureBuilder()
        cls.sr = build_minimal_sr(builder, "Reader")
        cls.sr_id = str(cls.sr.pk)
        attached = ProcessRequirementService().requirement_ids_by_permit(
            [cls.sr_id], graph_slug=GraphSlugs.BCAP_SERVICE_REQUEST
        )
        cls.requirement_id = next(iter(attached[cls.sr_id]))

    def _by_id(self, ids):
        return self.service._requirements_by_id(ids)

    def test_reads_the_card_fields_off_the_tiles(self):
        requirement = self._by_id([self.requirement_id])[self.requirement_id]

        self.assertEqual(requirement.name, "Outstanding")
        # The raw tile value, not an Arches-formatted display value.
        self.assertEqual(requirement.due_date, "2026-03-01")
        self.assertEqual(requirement.route, self.requirement_id)

    def test_a_requirement_with_no_tiles_is_still_unsatisfied(self):
        # A deleted requirement leaves the SR's reference dangling; it now
        # seeds a blank entry rather than vanishing from the lookup.
        gone = str(uuid4())

        requirement = self._by_id([gone])[gone]

        self.assertEqual(requirement.name, "")
        self.assertEqual(requirement.due_date, "")
        self.assertEqual(requirement.route, gone)

    def test_deleting_the_requirement_drops_the_sr_off_the_dashboard(self):
        # Arches scrubs the reference out of the SR's child tile on delete,
        # so the SR has no active requirement left to surface.
        Resource.objects.get(pk=self.requirement_id).delete()

        page = self.service.get_cards(DashboardFilter())

        self.assertNotIn(self.sr_id, [card.id for card in page.results])

    def test_a_satisfied_requirement_is_left_out(self):
        satisfied = FixtureBuilder().make_process_requirement(
            {
                "id": "REQ-DONE",
                "name": "Done",
                "due": "2026-01-01",
                "notes": "",
                "satisfied": True,
                "sub_requirements": [],
            }
        )

        self.assertEqual(self._by_id([str(satisfied.pk)]), {})


class DashboardUnresolvedRollupTests(TestCase):
    """The unresolved-thread roll-up: an SR's card count spans threads on the
    SR and on the host resources its process requirements' submission_data
    points at (its related investigation/alteration/inspection)."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = InternalDashboardService()
        builder = FixtureBuilder()
        cls.sr, cls.host, requirement = build_sr_with_investigation(builder, "Roll")
        cls.sr_id = str(cls.sr.pk)
        cls.host_id = str(cls.host.pk)
        cls.requirement = requirement
        cls.requirement_id = str(requirement.pk)

    def test_context_ids_include_the_sr_its_requirement_and_the_host(self):
        contexts = (
            BcapServiceRequestService().submission_context_ids_for_service_requests(
                [self.sr]
            )
        )
        self.assertEqual(
            contexts,
            {self.sr_id: {self.sr_id, self.requirement_id, self.host_id}},
        )

    def test_an_sr_with_no_submission_maps_to_itself_and_its_requirement(self):
        builder = FixtureBuilder()
        requirement = make_requirement(builder, "Bare")
        bare = build_service_request(builder, "Bare", [RequirementRow(requirement)])
        contexts = (
            BcapServiceRequestService().submission_context_ids_for_service_requests(
                [bare]
            )
        )
        self.assertEqual(contexts, {str(bare.pk): {str(bare.pk), str(requirement.pk)}})

    def test_card_count_rolls_up_threads_on_the_sr_and_the_host(self):
        builder = FixtureBuilder()
        _, reader = make_party(builder, "roller", "Ray", "Reader", internal=True)
        # One open thread on the SR, its requirement and its submission
        # host, and one resolved that must not count.
        make_message(builder, context=self.sr, recipient=reader, subject="p")
        make_message(builder, context=self.host, recipient=reader, subject="h")
        make_message(builder, context=self.requirement, recipient=reader, subject="req")
        make_message(
            builder,
            context=self.host,
            recipient=reader,
            resolved_date="2026-02-01",
            subject="resolved",
        )

        page = self.service.get_cards(DashboardFilter(), "roller")

        card = next(c for c in page.results if c.id == self.sr_id)
        self.assertEqual(card.unresolved_messages, 3)
