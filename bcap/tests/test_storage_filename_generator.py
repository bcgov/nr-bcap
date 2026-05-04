import os
from unittest.mock import MagicMock

from django.test import TestCase

from bcap.util import storage_filename_generator
from bcap.util.storage_filename_generator import generate_filename


class TestGenerateFilename(TestCase):
    def setUp(self):
        for attr in ("borden_number_node", "borden_number_datatype"):
            if hasattr(generate_filename, attr):
                delattr(generate_filename, attr)

        mock_node = MagicMock()
        mock_node.datatype = "string"

        self.mock_datatype = MagicMock()
        self.mock_models = MagicMock()
        self.mock_models.Node.objects.filter.return_value.first.return_value = mock_node
        self.mock_models.TileModel.objects.filter.return_value.first.return_value = None

        self.mock_datatypes = MagicMock()
        self.mock_datatypes.datatypes.DataTypeFactory.return_value.get_instance.return_value = (
            self.mock_datatype
        )

        storage_filename_generator.models = self.mock_models
        storage_filename_generator.datatypes = self.mock_datatypes

    def _instance(
        self, slug="my-graph", resource_id="rid", node_alias="site_photograph"
    ):
        inst = MagicMock()
        inst.tile.resourceinstance.graph.slug = slug
        inst.tile.resourceinstance.resourceinstanceid = resource_id
        inst.tile.nodegroup.grouping_node.alias = node_alias
        return inst

    def test_borden_number_splits_into_path_segments(self):
        self.mock_datatype.get_display_value.return_value = "EeRm-123"
        self.mock_models.TileModel.objects.filter.return_value.first.return_value = (
            MagicMock()
        )

        result = generate_filename(self._instance(), "photo.jpg")

        self.assertEqual(
            result,
            os.path.join("my-graph", "EeRm", "123", "site_photograph", "photo.jpg"),
        )

    def test_no_borden_tile_uses_resource_id(self):
        result = generate_filename(self._instance(), "report.pdf")

        self.assertEqual(
            result, os.path.join("my-graph", "rid", "site_photograph", "report.pdf")
        )

    def test_no_graph_slug_uses_system_settings(self):
        inst = self._instance(slug="")

        result = generate_filename(inst, "data.csv")

        self.assertTrue(result.startswith("system_settings"))
