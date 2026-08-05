"""Unit tests for the two exposed ProcessRequirementService methods: clone (one
template -> one is_template_requirement=False working copy) and
create_working_copies (a copy of every template, in flow order)."""

from datetime import datetime
from uuid import uuid4

from django.test import SimpleTestCase, TestCase

from arches.app.models.models import TileModel

from arches_querysets.models import ResourceTileTree

from bcap.serializers.process_requirement_serializers import ChecklistStep
from bcap.services.dashboard.dashboard_types import DashboardFilter
from bcap.services.dashboard.internal_dashboard_service import (
    InternalDashboardService,
)
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.util.bcap_aliases import GraphSlugs
from bcap.builders.process_requirement_builder import ProcessRequirementBuilder
from bcap.services.process_requirement.template_specs import (
    host_graph,
    load,
    module_graph,
    supported_permit_types,
)
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


def _assignee_of(module, requirement_id):
    """The requirement child's ministry_assignee id, or None."""
    child = _module_children(module)[str(requirement_id)]
    assignee = child.aliased_data.ministry_assignee
    return str(assignee.pk) if assignee else None


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


class TemplateSpecTests(SimpleTestCase):
    """The group-file lookups that decide where a module's own submission
    lives. Plain JSON reads, so no database."""

    def test_module_graph_defaults_to_the_permit_type(self):
        # Only the permit group names a graph; the rest are their own type.
        self.assertEqual(module_graph("permit"), GraphSlugs.PERMIT_APPLICATION)
        self.assertEqual(module_graph("investigation"), GraphSlugs.INVESTIGATION)

    def test_host_graph_is_the_child_matching_the_modules_graph(self):
        # The permit module hosts its submission on the permit itself.
        self.assertEqual(host_graph("permit"), GraphSlugs.PERMIT_APPLICATION)
        self.assertEqual(host_graph("investigation"), GraphSlugs.INVESTIGATION)

    def test_an_unsupported_permit_type_has_no_host_graph(self):
        self.assertNotIn("nonsense", supported_permit_types())
        self.assertIsNone(host_graph("nonsense"))

    def test_every_supported_type_loads(self):
        for permit_type in supported_permit_types():
            with self.subTest(permit_type=permit_type):
                spec = load(permit_type)
                self.assertTrue(spec["name"])
                self.assertTrue(spec["requirements"])


class ProcessRequirementServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.templates = seed_requirement_templates(ProcessRequirementBuilder())
        cls.template_pks = {template.pk for template in cls.templates}

    def setUp(self):
        self.service = ProcessRequirementService()

    def _trees(self, *resources):
        """The requirement trees, in the order asked for. Building a tile tree
        is the expensive part of these tests, so load them in one call and read
        every assertion off the result."""
        loaded = {
            str(tree.pk): tree
            for tree in ResourceTileTree.get_tiles(
                GraphSlugs.PROCESS_REQUIREMENT,
                resource_ids=[resource.pk for resource in resources],
            )
        }
        return [loaded[str(resource.pk)] for resource in resources]

    def _tree(self, resource):
        return self._trees(resource)[0]

    def _identification(self, tree):
        return tree.aliased_data.requirement_identification.aliased_data

    def _is_template(self, tree):
        flag = self._identification(tree).is_template_requirement
        return flag.aliased_data.is_template_requirement

    def _name(self, tree):
        return localized_string(self._identification(tree).requirement_name)

    def _sub_requirements(self, tree):
        return tree.aliased_data.requirement_data.aliased_data.sub_requirement_n1

    def test_clone_makes_an_editable_non_template_copy(self):
        template = self.templates[0]
        copy = self.service.builder.clone_requirement(template.pk)

        copy_tree, template_tree = self._trees(copy, template)
        self.assertNotIn(copy.pk, self.template_pks)
        self.assertFalse(self._is_template(copy_tree))
        self.assertEqual(len(self._sub_requirements(copy_tree)), 1)
        # The source template is left intact for the next clone.
        self.assertTrue(self._is_template(template_tree))

    def test_clone_by_id_makes_a_non_template_copy(self):
        copy = self.service.clone_by_id(self.templates[0].pk)
        self.assertNotIn(copy.pk, self.template_pks)
        self.assertFalse(self._is_template(self._tree(copy)))

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
        for tree in self._trees(*children):
            self.assertFalse(self._is_template(tree))

    def test_create_working_copies_copies_every_template_in_flow_order(self):
        copies = self.service.create_working_copies().requirements

        # The default module's child requirements, in flow order (seeded by
        # migration, so independent of this test's fixture templates).
        expected = [child["name"] for child in load("permit")["requirements"]]
        trees = self._trees(*copies)
        self.assertEqual([self._name(tree) for tree in trees], expected)
        for tree in trees:
            self.assertFalse(self._is_template(tree))

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
                ChecklistStep(name="First", description="one"),
                ChecklistStep(name="Second", description="two"),
            ],
        )

        steps = self._sub_requirements(self._tree(requirement))
        self.assertEqual(len(steps), 2)
        kept_tileid = steps[0].tileid
        dropped_tileid = steps[1].tileid

        # Rename the kept step, drop the second, add a third.
        self.service.save_checklist(
            requirement.pk,
            "Checklist v2",
            [
                ChecklistStep(tileid=kept_tileid, name="First edited", description=""),
                ChecklistStep(name="Third", description="three"),
            ],
        )

        tree = self._tree(requirement)
        after = self._sub_requirements(tree)
        names = [localized_string(s.aliased_data.checklist_item_name) for s in after]
        self.assertEqual(names, ["First edited", "Third"])
        # The kept step is the same tile, updated in place (not recreated).
        self.assertEqual(after[0].tileid, kept_tileid)
        # The dropped step's tile is deleted, not orphaned.
        self.assertFalse(TileModel.objects.filter(pk=dropped_tileid).exists())
        # The partial save left the requirement's identification intact.
        self.assertEqual(self._name(tree), "Checklist v2")
        self.assertFalse(self._is_template(tree))


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

        # A second permit, unassigned so its first assignment registers as an
        # edit-log change, and foreign to the permit above.
        other = build_unassigned_permit(FixtureBuilder(), "Other Permit")
        other_module = _load_module(other.pk)
        cls.other_permit_id = str(other.pk)
        cls.other_module_tileid = str(other_module.tileid)
        cls.other_requirement_id = next(iter(_module_children(other_module)))

    def setUp(self):
        self.service = ProcessRequirementService()

    def _assignee(self, requirement_id, permit_id=None, module_index=0):
        module = _load_module(permit_id or self.permit_id, module_index)
        return _assignee_of(module, requirement_id)

    def _assign(self, requirement_id, contributor_id):
        return self.service.set_ministry_assignee(
            self.permit_id, self.module_tileid, requirement_id, contributor_id
        )

    def test_assign_and_clear_leave_the_modules_other_nodes_intact(self):
        before = _snapshot(_load_module(self.permit_id))

        self.assertTrue(self._assign(self.assessment_id, self.ada_id))

        module = _load_module(self.permit_id)
        self.assertEqual(_snapshot(module), before)
        self.assertEqual(_assignee_of(module, self.assessment_id), self.ada_id)
        self.assertEqual(_assignee_of(module, self.review_id), self.ada_id)

        self.assertTrue(self._assign(self.assessment_id, None))

        module = _load_module(self.permit_id)
        self.assertIsNone(_assignee_of(module, self.assessment_id))
        self.assertEqual(_snapshot(module), before)

    def test_a_module_or_requirement_that_isnt_this_permits_is_rejected(self):
        # An unknown module, another permit's requirement, and another permit's
        # module tile all fail rather than reaching across applications.
        self.assertFalse(
            self.service.set_ministry_assignee(
                self.permit_id, uuid4(), self.assessment_id, self.ada_id
            )
        )
        self.assertFalse(self._assign(self.other_requirement_id, self.ada_id))
        self.assertFalse(
            self.service.set_ministry_assignee(
                self.permit_id,
                self.other_module_tileid,
                self.other_requirement_id,
                self.ada_id,
            )
        )
        self.assertIsNone(
            self._assignee(self.other_requirement_id, permit_id=self.other_permit_id)
        )

    def test_assignment_date_surfaces_on_the_internal_dashboard(self):
        # The date is derived from the edit log, so it only appears once the
        # assignee node's value has actually changed.
        def assign(contributor_id):
            self.assertTrue(
                self.service.set_ministry_assignee(
                    self.other_permit_id,
                    self.other_module_tileid,
                    self.other_requirement_id,
                    contributor_id,
                )
            )
            return self._card(self.other_permit_id)

        first = assign(self.ada_id)
        self.assertEqual(first.ministry_assignee_id, self.ada_id)
        self.assertTrue(first.ministry_assignee_change_date)

        second = assign(self.grace_id)
        self.assertEqual(second.ministry_assignee_id, self.grace_id)
        self.assertGreater(
            datetime.fromisoformat(second.ministry_assignee_change_date),
            datetime.fromisoformat(first.ministry_assignee_change_date),
        )

    @staticmethod
    def _card(permit_id):
        page = InternalDashboardService().get_cards(DashboardFilter())
        return next(card for card in page.results if card.id == permit_id)
