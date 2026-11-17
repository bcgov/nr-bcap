"""The save hook that stamps a fresh sequence id on the first save of any
resource model with a reference-number-widget node: the id is always assigned
on the first save (overwriting any value a cloned template carried in), while
a re-save of an existing tile is left alone.

Shared behaviour is exercised via _AssignIdMixin against both the
Permit Application (APP-YYYY-N) and BCAP Service Request (REQ-YYYY-N) graphs."""

from types import SimpleNamespace
from uuid import uuid4

from django.test import TestCase

from arches.app.models.models import ResourceInstance, TileModel

from bcap.functions.assign_application_id import AssignApplicationId
from bcap.util.aliases.bcap_service_request import BcapServiceRequestAliases
from bcap.util.aliases.permit_application import PermitApplicationAliases
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import get_node


class _AssignIdMixin:
    """Shared tests for AssignApplicationId. Concrete subclasses supply
    ``graph_slug``, ``node_alias``, and ``expected_pattern``."""

    graph_slug: str
    node_alias: str
    expected_pattern: str

    @classmethod
    def setUpTestData(cls):
        cls.node = get_node(cls.graph_slug, cls.node_alias)
        cls.node_id = str(cls.node.pk)

    def setUp(self):
        self.function = AssignApplicationId()

    def _unsaved_tile(self, data=None):
        """A tile mock whose pk does not yet exist in TileModel."""
        return SimpleNamespace(
            pk=uuid4(),
            nodegroup_id=self.node.nodegroup_id,
            data=data or {},
            resourceinstance=SimpleNamespace(
                graph=SimpleNamespace(slug=self.graph_slug)
            ),
        )

    def test_first_save_assigns_a_sequence_id(self):
        tile = self._unsaved_tile()

        self.function.save(tile, request=None)

        self.assertRegex(tile.data[self.node_id], self.expected_pattern)

    def test_first_save_overwrites_a_copied_id(self):
        # A clone arrives carrying the source's id; the first save replaces it.
        tile = self._unsaved_tile({self.node_id: "STALE"})

        self.function.save(tile, request=None)

        self.assertRegex(tile.data[self.node_id], self.expected_pattern)

    def test_existing_tile_keeps_its_id(self):
        resource = ResourceInstance.objects.create(graph_id=self.node.graph_id)
        saved = TileModel.objects.create(
            resourceinstance=resource, nodegroup_id=self.node.nodegroup_id, data={}
        )
        kept = "ID-ALREADY-SET"
        tile = SimpleNamespace(
            pk=saved.pk,
            data={self.node_id: kept},
            resourceinstance=SimpleNamespace(
                graph=SimpleNamespace(slug=self.graph_slug)
            ),
        )

        self.function.save(tile, request=None)

        self.assertEqual(tile.data[self.node_id], kept)

    def test_wrong_nodegroup_leaves_data_untouched(self):
        # A tile in a different nodegroup (not the reference-number one) must
        # leave data untouched rather than try to stamp it.
        tile = SimpleNamespace(
            pk=uuid4(),
            nodegroup_id=uuid4(),  # a random, non-matching nodegroup
            data={},
            resourceinstance=SimpleNamespace(
                graph=SimpleNamespace(slug=self.graph_slug)
            ),
        )

        self.function.save(tile, request=None)

        self.assertEqual(tile.data, {})


class PermitApplicationAssignIdTests(_AssignIdMixin, TestCase):
    graph_slug = GraphSlugs.PERMIT_APPLICATION
    node_alias = PermitApplicationAliases.APPLICATION_ID
    expected_pattern = r"^APP-\d{4}-\d+$"


class BcapServiceRequestAssignIdTests(_AssignIdMixin, TestCase):
    graph_slug = GraphSlugs.BCAP_SERVICE_REQUEST
    node_alias = BcapServiceRequestAliases.SERVICE_REQUEST_ID
    expected_pattern = r"^REQ-\d{4}-\d+$"
