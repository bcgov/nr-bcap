"""Unit tests for the seed service: given a permit and a type, it creates a
grouping parent plus four requirements, links each to its module resource, and
attaches the four to the permit in flow order."""

from django.test import TestCase

from arches_querysets.models import ResourceTileTree

from bcap.services.process_requirement.process_requirement_seed_service import (
    ProcessRequirementSeedService,
)
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.dashboard.resource_builder import ResourceBuilder


def _make_permit(builder):
    """A minimal permit_application with an identification tile."""
    permit = builder.new_resource(GraphSlugs.PERMIT_APPLICATION)
    builder.append_blank_tile_for_group(
        permit,
        "application_identification",
        {
            "application_id": builder.localized("APP-TEST"),
            "project_name": builder.localized("Test Project"),
        },
    )
    permit.save(**builder.save_kwargs)
    return permit


class ProcessRequirementSeedServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.permit = _make_permit(ResourceBuilder())

    def _requirement(self, pk):
        return ResourceTileTree.get_tiles(
            GraphSlugs.PROCESS_REQUIREMENT, resource_ids=[pk]
        ).get()

    def _template_data(self, pk):
        ident = self._requirement(pk).aliased_data.requirement_identification
        return ident.aliased_data.is_template_requirement.aliased_data

    def test_seed_creates_parent_and_four_requirements(self):
        result = ProcessRequirementSeedService().seed(
            self.permit.pk, GraphSlugs.INSPECTION
        )

        self.assertEqual(len(result["requirements"]), 4)
        for req in [result["parent"], *result["requirements"]]:
            self.assertFalse(self._template_data(req.pk).is_template_requirement)

    def test_proponent_rows_link_a_module_and_checklists_do_not(self):
        result = ProcessRequirementSeedService().seed(
            self.permit.pk, GraphSlugs.INSPECTION
        )
        reqs = result["requirements"]

        # Row 0 (Document Approach) links a new module resource.
        approach = self._requirement(reqs[0].pk)
        submission = approach.aliased_data.requirement_data.aliased_data.submission_data
        self.assertIsNotNone(submission.aliased_data.submission_data)
        # Row 1 (Review Approach) is a checklist with nothing linked.
        review = self._requirement(reqs[1].pk)
        self.assertIsNone(review.aliased_data.requirement_data)

    def test_who_maps_to_is_internal_requirement(self):
        result = ProcessRequirementSeedService().seed(
            self.permit.pk, GraphSlugs.INSPECTION
        )
        flags = [
            self._template_data(r.pk).is_internal_requirement
            for r in result["requirements"]
        ]
        # Proponent, Permitting Arch, Proponent, Permitting Arch.
        self.assertEqual(flags, [False, True, False, True])

    def test_requirements_attach_to_the_permit_in_order(self):
        result = ProcessRequirementSeedService().seed(
            self.permit.pk, GraphSlugs.INVESTIGATION
        )

        permit = ResourceTileTree.get_tiles(
            GraphSlugs.PERMIT_APPLICATION, resource_ids=[self.permit.pk]
        ).get()
        admin = permit.aliased_data.application_admin
        children = admin.aliased_data.process_requirement
        linked_ids = {
            child.aliased_data.process_requirement.pk for child in children
        }
        for req in result["requirements"]:
            self.assertIn(req.pk, linked_ids)
        # The grouping parent is not attached.
        self.assertNotIn(result["parent"].pk, linked_ids)
        orders = [c.aliased_data.process_requirement_order for c in children]
        self.assertEqual(orders, sorted(orders))
