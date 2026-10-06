import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import TestCase

from arches.app.models.models import Node

from bcap.util import storage_filename_generator
from bcap.util.storage_filename_generator import generate_filename
from tests.services.records.test_classification import reference_value


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

    def _instance(self, slug="my-graph", resource_id="rid", tile_id="tile-uuid"):
        inst = MagicMock()
        inst.tile.resourceinstance.graph.slug = slug
        inst.tile.resourceinstance.resourceinstanceid = resource_id
        inst.tile.tileid = tile_id
        return inst

    def test_borden_number_splits_into_path_segments(self):
        self.mock_datatype.get_display_value.return_value = "EeRm-123"
        self.mock_models.TileModel.objects.filter.return_value.first.return_value = (
            MagicMock()
        )

        result = generate_filename(self._instance(), "photo.jpg")

        self.assertEqual(
            result,
            os.path.join("my-graph", "EeRm", "123", "photo-tile-uuid.jpg"),
        )

    def test_no_borden_tile_uses_resource_id(self):
        result = generate_filename(self._instance(), "report.pdf")

        self.assertEqual(
            result, os.path.join("my-graph", "rid", "report-tile-uuid.pdf")
        )

    def test_no_graph_slug_uses_system_settings(self):
        inst = self._instance(slug="")

        result = generate_filename(inst, "data.csv")

        self.assertTrue(result.startswith("system_settings"))

    def _site_image(self, doc_type):
        """A site image, saved in the site images nodegroup."""
        self.enterContext(
            patch.object(
                Node.objects,
                "filter",
                return_value=[
                    SimpleNamespace(alias="site_images", nodeid="n-file"),
                    SimpleNamespace(alias="image_type", nodeid="n-type"),
                ],
            )
        )
        inst = self._instance(slug="archaeological_site")
        inst.tile.data = {"n-type": reference_value(("fr", "Carte"), ("en", doc_type))}
        return inst

    def test_upload_is_tagged(self):
        inst = self._site_image("Map")
        result = generate_filename(inst, "photo.jpg")

        self.assertEqual(
            result, os.path.join("archaeological_site", "rid", "photo-tile-uuid.jpg")
        )
        tags = inst.path.file.records_tags
        self.assertEqual(tags.orcs_classification, "11300-35")
        self.assertEqual(tags.sensitivity_class, "site-location")
        self.assertEqual(tags.classification_status, "auto")

    def test_unlisted_type_is_flagged_for_review(self):
        inst = self._site_image("Something New")
        generate_filename(inst, "photo.jpg")

        self.assertEqual(
            inst.path.file.records_tags.classification_status, "needs-review"
        )

    def test_unknown_node_is_unclassified(self):
        inst = self._instance()
        generate_filename(inst, "report.pdf")

        self.assertEqual(
            inst.path.file.records_tags.classification_status, "unclassified"
        )
