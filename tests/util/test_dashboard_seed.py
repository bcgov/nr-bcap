from django.test import SimpleTestCase, TestCase

from arches.app.models.models import GraphModel, Node, ResourceXResource

from arches_controlled_lists.models import ListItem
from arches_querysets.models import ResourceTileTree

from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.dashboard.dashboard_seed import DashboardDemoBuilder

from tests.controlled_list_fixtures import SeedControlledListsMixin


class LocalizedTests(SimpleTestCase):
    def test_wraps_value_in_string_datatype_shape(self):
        self.assertEqual(
            DashboardDemoBuilder.localized("Review"),
            {"en": {"value": "Review", "direction": "ltr"}},
        )


class ReferenceValueTests(SeedControlledListsMixin, TestCase):
    """reference_value resolves a node's controlled list to a single item id."""

    def test_returns_item_matching_label(self):
        result = DashboardDemoBuilder.reference_value(
            "hca_permit", "hca_permit_type", "Investigation"
        )

        self.assertEqual(len(result), 1)
        item = ListItem.objects.get(pk=result[0])
        self.assertTrue(item.list_item_values.filter(value="Investigation").exists())

    def test_returns_first_item_by_sort_order_when_no_label(self):
        node = Node.objects.get(
            graph__slug="contributor",
            alias="contributor_type",
            source_identifier=None,
        )
        list_id = node.config.get("controlledList")
        expected = (
            ListItem.objects.filter(list_id=list_id).order_by("sortorder").first()
        )

        result = DashboardDemoBuilder.reference_value("contributor", "contributor_type")

        self.assertEqual(result, [str(expected.pk)])

    def test_raises_when_list_has_no_matching_item(self):
        with self.assertRaises(RuntimeError):
            DashboardDemoBuilder.reference_value(
                "contributor", "contributor_type", "Nope"
            )


class BuildDashboardDemoDataTests(SeedControlledListsMixin, TestCase):
    """Integration test for the full builder."""

    def _slug(self, resource):
        return GraphModel.objects.get(pk=resource.graph_id).slug

    def _link_targets(self, resource):
        return {
            str(rxr.to_resource_id)
            for rxr in ResourceXResource.objects.filter(from_resource_id=resource.pk)
        }

    def test_creates_resources_on_the_expected_graphs(self):
        data = DashboardDemoBuilder().build()

        self.assertEqual(self._slug(data.assignees[0]), "contributor")
        self.assertEqual(self._slug(data.holders[0]), "contributor")
        self.assertEqual(self._slug(data.hca_permit), "hca_permit")
        self.assertEqual(
            self._slug(data.process_requirements[0]), "process_requirement"
        )
        self.assertEqual(self._slug(data.permit), "permit_application")
        for requirement in data.process_requirements:
            self.assertFalse(self._is_template(requirement))

    def _is_template(self, requirement):
        tree = ResourceTileTree.get_tiles(
            GraphSlugs.PROCESS_REQUIREMENT, resource_ids=[requirement.pk]
        ).get()
        identification = tree.aliased_data.requirement_identification.aliased_data
        return (
            identification.is_template_requirement.aliased_data.is_template_requirement
        )

    def test_links_permit_to_its_related_resources(self):
        data = DashboardDemoBuilder().build()

        # related_permit -> HCA permit, the application_admin's project_officer,
        # plus each application_admin child's process_requirement and
        # ministry_assignee links (one child per requirement).
        self.assertEqual(
            self._link_targets(data.permit),
            {str(data.hca_permit.pk), str(data.project_officer.pk)}
            | {str(req.pk) for req in data.process_requirements}
            | {str(assignee.pk) for assignee in data.assignees},
        )
        # HCA permit's permit_holder points at every holder contributor.
        self.assertEqual(
            self._link_targets(data.hca_permit),
            {str(holder.pk) for holder in data.holders},
        )
