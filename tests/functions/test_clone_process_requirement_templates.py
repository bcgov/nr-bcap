"""The permit application save hook that snapshots process-requirement
templates: a link to a template is swapped for a fresh working copy in save, and
an existing working copy is left alone (no re-clone on re-save)."""

from types import SimpleNamespace

from django.test import TestCase

from arches_querysets.models import ResourceTileTree

from bcap.functions.clone_process_requirement_templates import (
    CloneProcessRequirementTemplates,
)
from bcap.util.aliases.permit_application import PermitApplicationAliases
from bcap.util.bcap_aliases import GraphSlugs
from bcap.builders.process_requirement_builder import ProcessRequirementBuilder
from bcap.util.graph import get_node

from tests.permit_fixtures import seed_requirement_templates


def relationship(resource_id):
    return {
        "resourceId": str(resource_id),
        "ontologyProperty": "",
        "inverseOntologyProperty": "",
    }


class CloneProcessRequirementTemplatesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.template = seed_requirement_templates(ProcessRequirementBuilder())[0]
        cls.node_id = str(
            get_node(
                GraphSlugs.PERMIT_APPLICATION,
                PermitApplicationAliases.PROCESS_REQUIREMENT,
            ).pk
        )

    def setUp(self):
        self.function = CloneProcessRequirementTemplates()

    def _tile(self, resource_id):
        return SimpleNamespace(data={self.node_id: [relationship(resource_id)]})

    def _is_template(self, resource_id):
        return (
            ResourceTileTree.get_tiles(GraphSlugs.PROCESS_REQUIREMENT)
            .filter(pk=resource_id, is_template_requirement=True)
            .exists()
        )

    def test_template_link_is_swapped_for_a_non_template_clone(self):
        tile = self._tile(self.template.pk)

        self.function.save(tile, request=None)

        swapped = tile.data[self.node_id][0]["resourceId"]
        self.assertNotEqual(swapped, str(self.template.pk))
        self.assertFalse(self._is_template(swapped))
        self.assertEqual(tile._cloned_requirement_ids, [swapped])

    def test_existing_working_copy_is_not_recloned(self):
        # First save clones the template; a second save sees the working copy
        # (not a template) and leaves it untouched.
        tile = self._tile(self.template.pk)
        self.function.save(tile, request=None)
        clone_id = tile.data[self.node_id][0]["resourceId"]
        self.assertFalse(self._is_template(clone_id))

        self.function.save(tile, request=None)

        self.assertEqual(tile.data[self.node_id][0]["resourceId"], clone_id)
        self.assertEqual(tile._cloned_requirement_ids, [])
