"""Unit tests for the two exposed ProcessRequirementService methods: clone (one
template -> one is_template_requirement=False working copy) and
create_working_copies (a copy of every template, in flow order)."""

from datetime import datetime
from uuid import uuid4

from django.test import TestCase

from arches.app.models.models import TileModel

from arches_querysets.models import ResourceTileTree

from bcap.services.dashboard.dashboard_types import DashboardFilter
from bcap.services.dashboard.internal_dashboard_service import (
    InternalDashboardService,
)
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.util.bcap_aliases import GraphSlugs
from bcap.builders.process_requirement_builder import ProcessRequirementBuilder
from bcap.services.process_requirement.template_specs import load
from bcap.util.i18n import localized_string

from tests.builders import FixtureBuilder
from tests.controlled_list_fixtures import ControlledListFixtures
from tests.permit_fixtures import seed_requirement_templates
from tests.services.test_internal_dashboard_service import (
    build_permit_graph,
    build_unassigned_permit,
)


def _load_module(permit_id, index=0):
    """One of a permit's process_module tiles, fully hydrated."""
    permit = ResourceTileTree.get_tiles(
        GraphSlugs.PERMIT_APPLICATION, resource_ids=[str(permit_id)]
    ).get()
    return permit.aliased_data.application_admin.aliased_data.process_module[index]


def _module_children(module):
    """The module's process_requirement children that reference a requirement,
    keyed by requirement id."""
    return {
        str(child.aliased_data.process_requirement.pk): child
        for child in module.aliased_data.process_requirement or []
        if child.aliased_data.process_requirement
    }


def _snapshot(module):
    """The module's card nodes plus every child's flow order: everything
    set_ministry_assignee must leave alone."""
    return {
        "name": localized_string(module.aliased_data.module_name),
        "order": module.aliased_data.module_order,
        "requirement_orders": {
            requirement_id: child.aliased_data.process_requirement_order
            for requirement_id, child in _module_children(module).items()
        },
    }


class ProcessRequirementServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.templates = seed_requirement_templates(ProcessRequirementBuilder())
        cls.template_pks = {template.pk for template in cls.templates}

    def setUp(self):
        self.service = ProcessRequirementService()

    def _identification(self, resource):
        tree = ResourceTileTree.get_tiles(
            GraphSlugs.PROCESS_REQUIREMENT, resource_ids=[resource.pk]
        ).get()
        return tree.aliased_data.requirement_identification.aliased_data

    def _is_template(self, resource):
        flag = self._identification(resource).is_template_requirement
        return flag.aliased_data.is_template_requirement

    def _name(self, resource):
        return localized_string(self._identification(resource).requirement_name)

    def _sub_requirements(self, resource):
        tree = ResourceTileTree.get_tiles(
            GraphSlugs.PROCESS_REQUIREMENT, resource_ids=[resource.pk]
        ).get()
        return tree.aliased_data.requirement_data.aliased_data.sub_requirement_n1

    def test_clone_makes_an_editable_non_template_copy(self):
        template = self.templates[0]
        copy = self.service.builder.clone_requirement(template.pk)

        self.assertNotIn(copy.pk, self.template_pks)
        self.assertFalse(self._is_template(copy))
        self.assertEqual(len(self._sub_requirements(copy)), 1)
        # The source template is left intact for the next clone.
        self.assertTrue(self._is_template(template))

    def test_clone_by_id_makes_a_non_template_copy(self):
        copy = self.service.clone_by_id(self.templates[0].pk)
        self.assertNotIn(copy.pk, self.template_pks)
        self.assertFalse(self._is_template(copy))

    def test_templates_by_id_maps_the_seeded_templates(self):
        # Keyed by requirement identification; the values are the templates.
        by_id = self.service._templates_by_id()
        value_pks = {str(template.pk) for template in by_id.values()}
        self.assertIn(str(self.templates[0].pk), value_pks)

    def test_clone_module_links_submission_hosts(self):
        # A module with resource-bearing children (investigation) links each
        # child's submission without failing on the clone's existing
        # requirement_data tile.
        host = ProcessRequirementBuilder().make_resource(GraphSlugs.INVESTIGATION)
        children = self.service._clone_module("investigation", host).requirements

        expected = load("investigation")["requirements"]
        self.assertEqual(len(children), len(expected))
        for child in children:
            self.assertFalse(self._is_template(child))

    def test_create_working_copies_copies_every_template_in_flow_order(self):
        copies = self.service.create_working_copies().requirements

        # The default module's child requirements, in flow order (seeded by
        # migration, so independent of this test's fixture templates).
        expected = [child["name"] for child in load("permit")["requirements"]]
        self.assertEqual([self._name(copy) for copy in copies], expected)
        for copy in copies:
            self.assertFalse(self._is_template(copy))

    def test_module_hosts_uses_first_hosted_requirement_else_default(self):
        # A module files its messages against its first requirement (in flow
        # order) that has a submission host; a module whose requirements have no
        # host falls back to the permit itself, as does one with no requirements.
        requirements = {
            "module-hosted": ["req-a", "req-b"],
            "module-unhosted": ["req-c"],
            "module-empty": [],
        }
        hosts = {"req-a": set(), "req-b": {"host-b"}, "req-c": set()}
        result = ProcessRequirementService._module_hosts(
            requirements, hosts, default="permit-1"
        )
        self.assertEqual(
            result,
            {
                "module-hosted": "host-b",
                "module-unhosted": "permit-1",
                "module-empty": "permit-1",
            },
        )

    def test_update_checklist_edits_steps_in_place(self):
        # A checklist edit must reconcile the existing steps, not recreate them:
        # a kept step keeps its tile id, a removed one is deleted, and the rest
        # of the requirement (its identification) survives the partial save.
        requirement = self.service.builder.make_blank_checklist_requirement("Draft")
        self.service.save_checklist(
            requirement.pk,
            "Checklist",
            [
                {"name": "First", "description": "one"},
                {"name": "Second", "description": "two"},
            ],
        )

        steps = self._sub_requirements(requirement)
        self.assertEqual(len(steps), 2)
        kept_tileid = steps[0].tileid
        dropped_tileid = steps[1].tileid

        # Rename the kept step, drop the second, add a third.
        self.service.save_checklist(
            requirement.pk,
            "Checklist v2",
            [
                {"tileid": str(kept_tileid), "name": "First edited", "description": ""},
                {"name": "Third", "description": "three"},
            ],
        )

        after = self._sub_requirements(requirement)
        names = [localized_string(s.aliased_data.checklist_item_name) for s in after]
        self.assertEqual(names, ["First edited", "Third"])
        # The kept step is the same tile, updated in place (not recreated).
        self.assertEqual(after[0].tileid, kept_tileid)
        # The dropped step's tile is deleted, not orphaned.
        self.assertFalse(TileModel.objects.filter(pk=dropped_tileid).exists())
        # The partial save left the requirement's identification intact.
        self.assertEqual(self._name(requirement), "Checklist v2")
        self.assertFalse(self._is_template(requirement))


class MinistryAssigneeTests(TestCase):
    """set_ministry_assignee loads only the requirement and assignee nodes and
    then saves the permit partially, so the module's remaining nodes (its name,
    its order, and every child's flow order) must survive untouched."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        graph = build_permit_graph()
        cls.permit_id = str(graph.permit.pk)
        cls.assessment_id = str(graph.assessment.pk)
        cls.review_id = str(graph.review.pk)
        cls.ada_id = str(graph.ada.pk)
        cls.grace_id = str(graph.grace.pk)
        cls.module_tileid = str(_load_module(cls.permit_id).tileid)

    def setUp(self):
        self.service = ProcessRequirementService()

    def _assignee(self, requirement_id, permit_id=None, module_index=0):
        """The requirement child's ministry_assignee id, or None."""
        module = _load_module(permit_id or self.permit_id, module_index)
        assignee = _module_children(module)[
            str(requirement_id)
        ].aliased_data.ministry_assignee
        return str(assignee.pk) if assignee else None

    def _assign(self, requirement_id, contributor_id):
        return self.service.set_ministry_assignee(
            self.permit_id, self.module_tileid, requirement_id, contributor_id
        )

    def test_assign_and_clear_leave_the_modules_other_nodes_intact(self):
        before = _snapshot(_load_module(self.permit_id))

        self.assertTrue(self._assign(self.assessment_id, self.ada_id))

        self.assertEqual(_snapshot(_load_module(self.permit_id)), before)
        self.assertEqual(self._assignee(self.assessment_id), self.ada_id)
        # The sibling requirement's own assignee is untouched too.
        self.assertEqual(self._assignee(self.review_id), self.ada_id)

        # Clearing is the same narrowed load and partial save.
        self.assertTrue(self._assign(self.assessment_id, None))

        self.assertIsNone(self._assignee(self.assessment_id))
        self.assertEqual(_snapshot(_load_module(self.permit_id)), before)

    def test_a_module_or_requirement_that_isnt_this_permits_is_rejected(self):
        other = build_unassigned_permit(FixtureBuilder(), "Other Permit")
        other_module = _load_module(other.pk)
        foreign_requirement = next(iter(_module_children(other_module)))

        # An unknown module, another permit's requirement, and another permit's
        # module tile all fail rather than reaching across applications.
        self.assertFalse(
            self.service.set_ministry_assignee(
                self.permit_id, uuid4(), self.assessment_id, self.ada_id
            )
        )
        self.assertFalse(self._assign(foreign_requirement, self.ada_id))
        self.assertFalse(
            self.service.set_ministry_assignee(
                self.permit_id,
                str(other_module.tileid),
                foreign_requirement,
                self.ada_id,
            )
        )
        self.assertIsNone(self._assignee(foreign_requirement, permit_id=other.pk))

    def test_assignment_date_surfaces_on_the_internal_dashboard(self):
        # The date is derived from the edit log, so it only appears once the
        # assignee node's value has actually changed.
        permit = build_unassigned_permit(FixtureBuilder(), "Needs Owner")
        permit_id = str(permit.pk)
        module = _load_module(permit_id)
        requirement_id = next(iter(_module_children(module)))

        self.assertTrue(
            self.service.set_ministry_assignee(
                permit_id, str(module.tileid), requirement_id, self.ada_id
            )
        )
        first = self._card(permit_id)
        self.assertEqual(first.ministry_assignee_id, self.ada_id)
        self.assertTrue(first.ministry_assignee_change_date)

        self.assertTrue(
            self.service.set_ministry_assignee(
                permit_id, str(module.tileid), requirement_id, self.grace_id
            )
        )
        second = self._card(permit_id)
        self.assertEqual(second.ministry_assignee_id, self.grace_id)
        self.assertGreater(
            datetime.fromisoformat(second.ministry_assignee_change_date),
            datetime.fromisoformat(first.ministry_assignee_change_date),
        )

    @staticmethod
    def _card(permit_id):
        page = InternalDashboardService().get_cards(DashboardFilter())
        return next(card for card in page.results if card.id == permit_id)
