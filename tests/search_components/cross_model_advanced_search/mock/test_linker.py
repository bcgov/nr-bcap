from __future__ import annotations

from collections import defaultdict
from unittest.mock import MagicMock, patch

from typing_extensions import Any

from bcap.search_components.cross_model_advanced_search import Linker
from helper import _uuid


class TestLinkerGetConnected:
    @patch("bcap.search_components.cross_model_advanced_search.ResourceXResource")
    def test_empty_sources(self, mock_rxr: MagicMock) -> None:
        linker = Linker()
        result: set[str] = linker.get_connected(set())
        assert result == set()
        mock_rxr.objects.filter.assert_not_called()

    @patch("bcap.search_components.cross_model_advanced_search.ResourceXResource")
    def test_returns_forward_and_reverse(self, mock_rxr: MagicMock) -> None:
        rid1 = _uuid()
        rid2 = _uuid()
        rid3 = _uuid()

        forward_qs = MagicMock()
        forward_qs.values_list.return_value = [rid1]
        reverse_qs = MagicMock()
        reverse_qs.values_list.return_value = [rid2, rid3]

        mock_rxr.objects.filter.side_effect = [forward_qs, reverse_qs]

        linker = Linker()
        result: set[str] = linker.get_connected({_uuid()})
        assert result == {str(rid1), str(rid2), str(rid3)}

    @patch("bcap.search_components.cross_model_advanced_search.chunk")
    @patch("bcap.search_components.cross_model_advanced_search.ResourceXResource")
    def test_batches_large_source_set(self, mock_rxr: MagicMock, mock_chunk: MagicMock) -> None:
        sources = {_uuid() for _ in range(10)}
        batch1 = list(sources)[:5]
        batch2 = list(sources)[5:]

        mock_chunk.return_value = [batch1, batch2]

        forward_qs = MagicMock()
        forward_qs.values_list.return_value = []
        reverse_qs = MagicMock()
        reverse_qs.values_list.return_value = []

        mock_rxr.objects.filter.return_value = forward_qs
        mock_rxr.objects.filter.side_effect = [
            forward_qs, reverse_qs,
            forward_qs, reverse_qs,
        ]

        linker = Linker()
        linker.get_connected(sources)
        assert mock_rxr.objects.filter.call_count == 4

    @patch("bcap.search_components.cross_model_advanced_search.ResourceXResource")
    def test_single_source(self, mock_rxr: MagicMock) -> None:
        source = _uuid()
        target = _uuid()

        forward_qs = MagicMock()
        forward_qs.values_list.return_value = [target]
        reverse_qs = MagicMock()
        reverse_qs.values_list.return_value = []

        mock_rxr.objects.filter.side_effect = [forward_qs, reverse_qs]

        linker = Linker()
        result: set[str] = linker.get_connected({source})
        assert result == {str(target)}

    @patch("bcap.search_components.cross_model_advanced_search.ResourceXResource")
    def test_forward_and_reverse_overlap_deduplicated(self, mock_rxr: MagicMock) -> None:
        shared = _uuid()

        forward_qs = MagicMock()
        forward_qs.values_list.return_value = [shared]
        reverse_qs = MagicMock()
        reverse_qs.values_list.return_value = [shared]

        mock_rxr.objects.filter.side_effect = [forward_qs, reverse_qs]

        linker = Linker()
        result: set[str] = linker.get_connected({_uuid()})
        assert result == {str(shared)}

    @patch("bcap.search_components.cross_model_advanced_search.ResourceXResource")
    def test_no_connections(self, mock_rxr: MagicMock) -> None:
        forward_qs = MagicMock()
        forward_qs.values_list.return_value = []
        reverse_qs = MagicMock()
        reverse_qs.values_list.return_value = []

        mock_rxr.objects.filter.side_effect = [forward_qs, reverse_qs]

        linker = Linker()
        result: set[str] = linker.get_connected({_uuid()})
        assert result == set()


class TestLinkerGetIntermediate:
    @patch("bcap.search_components.cross_model_advanced_search.ResourceInstance")
    @patch("bcap.search_components.cross_model_advanced_search.ResourceXResource")
    def test_empty_sources(self, mock_rxr: MagicMock, mock_ri: MagicMock) -> None:
        linker = Linker()
        result: set[str] = linker.get_intermediate(set(), _uuid(), _uuid())
        assert result == set()

    @patch("bcap.search_components.cross_model_advanced_search.ResourceInstance")
    @patch("bcap.search_components.cross_model_advanced_search.ResourceXResource")
    def test_same_graph(self, mock_rxr: MagicMock, mock_ri: MagicMock) -> None:
        linker = Linker()
        sources = {_uuid(), _uuid()}
        graph = _uuid()
        result: set[str] = linker.get_intermediate(sources, graph, graph)
        assert result == sources


class TestLinkerGetLinkedFromTiles:
    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    @patch("bcap.search_components.cross_model_advanced_search.TileModel")
    def test_no_forward_links(self, mock_tile: MagicMock, mock_cache: MagicMock) -> None:
        mock_cache.get.return_value = []

        linker = Linker()
        result: dict[str, set[str]] = linker.get_linked_from_tiles(
            {_uuid()}, _uuid(), _uuid(), {_uuid()},
        )
        assert result == defaultdict(set)

    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    @patch("bcap.search_components.cross_model_advanced_search.TileModel")
    def test_no_matching_nodegroups(self, mock_tile: MagicMock, mock_cache: MagicMock) -> None:
        ng = _uuid()
        mock_cache.get.return_value = [{"node": _uuid(), "nodegroup": ng}]

        linker = Linker()
        result: dict[str, set[str]] = linker.get_linked_from_tiles(
            {_uuid()}, _uuid(), _uuid(), {_uuid()},
        )
        assert result == defaultdict(set)

    @patch("bcap.search_components.cross_model_advanced_search.chunk")
    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    @patch("bcap.search_components.cross_model_advanced_search.TileModel")
    def test_extracts_linked_ids(self, mock_tile_model: MagicMock, mock_cache: MagicMock, mock_chunk: MagicMock) -> None:
        ng = _uuid()
        node = _uuid()
        source_id = _uuid()
        linked_id = _uuid()

        mock_cache.get.return_value = [{"node": node, "nodegroup": ng}]
        mock_chunk.return_value = [[source_id]]

        mock_qs = MagicMock()
        mock_qs.values.return_value.iterator.return_value = [
            {
                "data": {node: [{"resourceId": linked_id}]},
                "resourceinstance_id": source_id,
            },
        ]
        mock_tile_model.objects.filter.return_value = mock_qs

        linker = Linker()
        result: dict[str, set[str]] = linker.get_linked_from_tiles(
            {source_id}, _uuid(), _uuid(), {ng},
        )
        assert result[source_id] == {linked_id}

    @patch("bcap.search_components.cross_model_advanced_search.chunk")
    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    @patch("bcap.search_components.cross_model_advanced_search.TileModel")
    def test_applies_tile_filters(self, mock_tile_model: MagicMock, mock_cache: MagicMock, mock_chunk: MagicMock) -> None:
        ng = _uuid()
        node = _uuid()
        filter_node = _uuid()
        source_id = _uuid()
        linked_id = _uuid()

        mock_cache.get.return_value = [{"node": node, "nodegroup": ng}]
        mock_chunk.return_value = [[source_id]]

        matching_tile = {
            "data": {node: [{"resourceId": linked_id}], filter_node: "expected"},
            "resourceinstance_id": source_id,
        }
        non_matching_tile = {
            "data": {node: [{"resourceId": _uuid()}], filter_node: "wrong"},
            "resourceinstance_id": source_id,
        }

        mock_qs = MagicMock()
        mock_qs.values.return_value.iterator.return_value = [matching_tile, non_matching_tile]
        mock_tile_model.objects.filter.return_value = mock_qs

        linker = Linker()
        result: dict[str, set[str]] = linker.get_linked_from_tiles(
            {source_id}, _uuid(), _uuid(), {ng},
            tile_filters={filter_node: {"op": "eq", "val": "expected"}},
        )
        assert linked_id in result[source_id]

    @patch("bcap.search_components.cross_model_advanced_search.chunk")
    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    @patch("bcap.search_components.cross_model_advanced_search.TileModel")
    def test_tile_missing_data_key(self, mock_tile_model: MagicMock, mock_cache: MagicMock, mock_chunk: MagicMock) -> None:
        ng = _uuid()
        node = _uuid()
        source_id = _uuid()

        mock_cache.get.return_value = [{"node": node, "nodegroup": ng}]
        mock_chunk.return_value = [[source_id]]

        mock_qs = MagicMock()
        mock_qs.values.return_value.iterator.return_value = [
            {
                "data": None,
                "resourceinstance_id": source_id,
            },
        ]
        mock_tile_model.objects.filter.return_value = mock_qs

        linker = Linker()
        result: dict[str, set[str]] = linker.get_linked_from_tiles(
            {source_id}, _uuid(), _uuid(), {ng},
        )
        assert source_id not in result or result[source_id] == set()

    @patch("bcap.search_components.cross_model_advanced_search.chunk")
    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    @patch("bcap.search_components.cross_model_advanced_search.TileModel")
    def test_tile_data_node_not_in_link_nodes(self, mock_tile_model: MagicMock, mock_cache: MagicMock, mock_chunk: MagicMock) -> None:
        ng = _uuid()
        node = _uuid()
        other_node = _uuid()
        source_id = _uuid()

        mock_cache.get.return_value = [{"node": node, "nodegroup": ng}]
        mock_chunk.return_value = [[source_id]]

        mock_qs = MagicMock()
        mock_qs.values.return_value.iterator.return_value = [
            {
                "data": {other_node: [{"resourceId": _uuid()}]},
                "resourceinstance_id": source_id,
            },
        ]
        mock_tile_model.objects.filter.return_value = mock_qs

        linker = Linker()
        result: dict[str, set[str]] = linker.get_linked_from_tiles(
            {source_id}, _uuid(), _uuid(), {ng},
        )
        assert source_id not in result or result[source_id] == set()

    @patch("bcap.search_components.cross_model_advanced_search.chunk")
    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    @patch("bcap.search_components.cross_model_advanced_search.TileModel")
    def test_multiple_sources_multiple_links(self, mock_tile_model: MagicMock, mock_cache: MagicMock, mock_chunk: MagicMock) -> None:
        ng = _uuid()
        node = _uuid()
        source_a = _uuid()
        source_b = _uuid()
        linked_a = _uuid()
        linked_b1 = _uuid()
        linked_b2 = _uuid()

        mock_cache.get.return_value = [{"node": node, "nodegroup": ng}]
        mock_chunk.return_value = [[source_a, source_b]]

        mock_qs = MagicMock()
        mock_qs.values.return_value.iterator.return_value = [
            {
                "data": {node: [{"resourceId": linked_a}]},
                "resourceinstance_id": source_a,
            },
            {
                "data": {node: [{"resourceId": linked_b1}, {"resourceId": linked_b2}]},
                "resourceinstance_id": source_b,
            },
        ]
        mock_tile_model.objects.filter.return_value = mock_qs

        linker = Linker()
        result: dict[str, set[str]] = linker.get_linked_from_tiles(
            {source_a, source_b}, _uuid(), _uuid(), {ng},
        )
        assert result[source_a] == {linked_a}
        assert result[source_b] == {linked_b1, linked_b2}

    @patch("bcap.search_components.cross_model_advanced_search.chunk")
    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    @patch("bcap.search_components.cross_model_advanced_search.TileModel")
    def test_tile_filter_rejects_all_tiles(self, mock_tile_model: MagicMock, mock_cache: MagicMock, mock_chunk: MagicMock) -> None:
        ng = _uuid()
        node = _uuid()
        filter_node = _uuid()
        source_id = _uuid()

        mock_cache.get.return_value = [{"node": node, "nodegroup": ng}]
        mock_chunk.return_value = [[source_id]]

        mock_qs = MagicMock()
        mock_qs.values.return_value.iterator.return_value = [
            {
                "data": {node: [{"resourceId": _uuid()}], filter_node: "wrong"},
                "resourceinstance_id": source_id,
            },
        ]
        mock_tile_model.objects.filter.return_value = mock_qs

        linker = Linker()
        result: dict[str, set[str]] = linker.get_linked_from_tiles(
            {source_id}, _uuid(), _uuid(), {ng},
            tile_filters={filter_node: {"op": "eq", "val": "expected"}},
        )
        assert source_id not in result or result[source_id] == set()

    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    @patch("bcap.search_components.cross_model_advanced_search.TileModel")
    def test_empty_source_ids(self, mock_tile: MagicMock, mock_cache: MagicMock) -> None:
        ng = _uuid()
        mock_cache.get.return_value = [{"node": _uuid(), "nodegroup": ng}]

        linker = Linker()
        result: dict[str, set[str]] = linker.get_linked_from_tiles(
            set(), _uuid(), _uuid(), {ng},
        )
        assert result == defaultdict(set)
