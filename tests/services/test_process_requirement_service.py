"""Unit tests for the two exposed ProcessRequirementService methods: clone (one
template -> one is_template_requirement=False working copy) and
create_working_copies (a copy of every template, in flow order)."""

from django.test import TestCase

from arches_querysets.models import ResourceTileTree

from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.dashboard.resource_builder import ResourceBuilder
from bcap.util.i18n import localized_string

from tests.permit_fixtures import seed_requirement_templates


class ProcessRequirementServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.templates = seed_requirement_templates(ResourceBuilder())
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
        copy = self.service.clone(template)

        self.assertNotIn(copy.pk, self.template_pks)
        self.assertFalse(self._is_template(copy))
        self.assertEqual(len(self._sub_requirements(copy)), 1)
        # The source template is left intact for the next clone.
        self.assertTrue(self._is_template(template))

    def test_create_working_copies_copies_every_template_in_flow_order(self):
        copies = self.service.create_working_copies()

        self.assertEqual(
            [self._name(copy) for copy in copies],
            ProcessRequirementService._TEMPLATE_NAMES,
        )
        self.assertTrue({copy.pk for copy in copies}.isdisjoint(self.template_pks))
        for copy in copies:
            self.assertFalse(self._is_template(copy))
