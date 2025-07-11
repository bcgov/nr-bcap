from unittest.mock import Mock

from arches.app.search.base_index import BaseIndex
from bcap.search_indexes.sample_index import SampleIndex
from django.test import TestCase


class TestSampleIndex(TestCase):
    def test_prepare_index(self):
        sample_index = SampleIndex(index_name="Sample Index")
        sample_index.prepare_index()

        expected_index_metadata = {
            "mappings": {
                "_doc": {
                    "properties": {
                        "tile_count": {"type": "keyword"},
                        "graph_id": {"type": "keyword"},
                    }
                }
            }
        }
        self.assertEqual(sample_index.index_metadata, expected_index_metadata)

    def test_get_documents_to_index(self):
        sample_index = SampleIndex(index_name="Sample Index")

        mock_resourceinstance = Mock(graph_id="test_graph_id")
        mock_tiles = [Mock(), Mock(), Mock()]  # Mock tiles list

        documents, doc_id = sample_index.get_documents_to_index(
            mock_resourceinstance, mock_tiles
        )

        self.assertEqual(
            documents,
            {"tile_count": len(mock_tiles), "graph_id": mock_resourceinstance.graph_id},
        )
        self.assertEqual(doc_id, str(mock_resourceinstance.resourceinstanceid))
