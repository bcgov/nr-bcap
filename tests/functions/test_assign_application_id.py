"""The permit application save hook that stamps the sequence application id: a
fresh APP-<n> is assigned on the first save (overwriting any value a cloned
template carried in), while a re-save of an existing tile is left alone."""

from types import SimpleNamespace
from uuid import uuid4

from django.test import TestCase

from arches.app.models.models import ResourceInstance, TileModel

from bcap.functions.assign_application_id import AssignApplicationId
from bcap.util.aliases.permit_application import PermitApplicationAliases
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import get_node
from bcap.util.i18n import localized_string


def string_value(text):
    return {"en": {"value": text, "direction": "ltr"}}


class AssignApplicationIdTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.node = get_node(
            GraphSlugs.PERMIT_APPLICATION, PermitApplicationAliases.APPLICATION_ID
        )
        cls.node_id = str(cls.node.pk)

    def setUp(self):
        self.function = AssignApplicationId()

    def _unsaved_tile(self, data=None):
        # A pk that isn't in the table yet is what the hook reads as a first save.
        return SimpleNamespace(pk=uuid4(), data=data or {})

    def test_first_save_assigns_a_sequence_id(self):
        tile = self._unsaved_tile()

        self.function.save(tile, request=None)

        self.assertRegex(localized_string(tile.data[self.node_id]), r"^APP-\d+$")

    def test_first_save_overwrites_a_copied_id(self):
        # A clone arrives carrying the source's id; the first save replaces it.
        tile = self._unsaved_tile({self.node_id: string_value("STALE")})

        self.function.save(tile, request=None)

        self.assertRegex(localized_string(tile.data[self.node_id]), r"^APP-\d+$")

    def test_existing_tile_keeps_its_id(self):
        permit = ResourceInstance.objects.create(graph_id=self.node.graph_id)
        saved = TileModel.objects.create(
            resourceinstance=permit, nodegroup_id=self.node.nodegroup_id, data={}
        )
        kept = string_value("APP-1")
        tile = SimpleNamespace(pk=saved.pk, data={self.node_id: kept})

        self.function.save(tile, request=None)

        self.assertEqual(tile.data[self.node_id], kept)
