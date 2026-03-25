from __future__ import annotations

from unittest.mock import MagicMock

from bcap.search_components.cross_model_advanced_search import Translator
from helper import _uuid


class TestTranslator:
    def test_same_graph_returns_sources(self) -> None:
        linker = MagicMock()
        translator = Translator(linker)
        sources = {_uuid(), _uuid()}
        graph = _uuid()

        result: set[str] = translator.translate(sources, graph, graph, {}, {})
        assert result == sources
        linker.get_intermediate.assert_not_called()

    def test_direct_link_found(self) -> None:
        linker = MagicMock()
        target_ids = {_uuid(), _uuid()}
        linker.get_intermediate.return_value = target_ids

        translator = Translator(linker)
        source = _uuid()
        target = _uuid()
        sources = {_uuid()}

        result: set[str] = translator.translate(sources, source, target, {}, {})
        assert result == target_ids

    def test_direct_link_empty_tries_multihop(self) -> None:
        linker = MagicMock()
        intermediate = _uuid()
        source = _uuid()
        target = _uuid()
        sources = {_uuid()}
        intermediate_ids = {_uuid()}
        target_ids = {_uuid()}

        linker.get_intermediate.side_effect = [
            set(),
            intermediate_ids,
            target_ids,
        ]
        linker.get_connected.return_value = set()

        adjacency = {
            source: [intermediate],
            intermediate: [target],
        }

        translator = Translator(linker)
        result: set[str] = translator.translate(sources, source, target, adjacency, {})
        assert result == target_ids

    def test_multihop_applies_es_filter(self) -> None:
        linker = MagicMock()
        source = _uuid()
        target = _uuid()
        intermediate = _uuid()
        sources = {_uuid()}

        common_id = _uuid()
        intermediate_ids = {common_id, _uuid()}
        es_matches_for_intermediate = {common_id}
        target_ids = {_uuid()}

        linker.get_intermediate.side_effect = [
            set(),
            intermediate_ids,
            target_ids,
        ]
        linker.get_connected.return_value = set()

        adjacency = {
            source: [intermediate],
            intermediate: [target],
        }

        translator = Translator(linker)
        result: set[str] = translator.translate(
            sources, source, target, adjacency, {intermediate: es_matches_for_intermediate},
        )
        assert result == target_ids

        third_call_args = linker.get_intermediate.call_args_list[2]
        assert third_call_args[0][0] == {common_id}

    def test_multihop_es_filter_eliminates_all_intermediates(self) -> None:
        linker = MagicMock()
        source = _uuid()
        target = _uuid()
        intermediate = _uuid()
        sources = {_uuid()}

        intermediate_ids = {_uuid(), _uuid()}
        es_matches_for_intermediate = {_uuid()}

        linker.get_intermediate.side_effect = [
            set(),
            intermediate_ids,
        ]
        linker.get_connected.return_value = set()

        adjacency = {
            source: [intermediate],
            intermediate: [target],
        }

        translator = Translator(linker)
        result: set[str] = translator.translate(
            sources, source, target, adjacency, {intermediate: es_matches_for_intermediate},
        )
        assert result == set()

    def test_multihop_skips_source_and_target_as_intermediate(self) -> None:
        linker = MagicMock()
        source = _uuid()
        target = _uuid()
        sources = {_uuid()}

        linker.get_intermediate.return_value = set()
        linker.get_connected.return_value = set()

        adjacency = {
            source: [target],
            target: [source],
        }

        translator = Translator(linker)
        result: set[str] = translator.translate(sources, source, target, adjacency, {})
        assert result == set()

    def test_multihop_no_reachable_intermediate(self) -> None:
        linker = MagicMock()
        source = _uuid()
        target = _uuid()
        intermediate = _uuid()
        sources = {_uuid()}

        linker.get_intermediate.return_value = set()
        linker.get_connected.return_value = set()

        adjacency = {
            source: [],
            intermediate: [target],
        }

        translator = Translator(linker)
        result: set[str] = translator.translate(sources, source, target, adjacency, {})
        assert result == set()

    def test_multihop_intermediate_reachable_via_reverse_adjacency(self) -> None:
        linker = MagicMock()
        source = _uuid()
        target = _uuid()
        intermediate = _uuid()
        sources = {_uuid()}

        intermediate_ids = {_uuid()}
        target_ids = {_uuid()}

        linker.get_intermediate.side_effect = [
            set(),
            intermediate_ids,
            target_ids,
        ]
        linker.get_connected.return_value = set()

        adjacency = {
            intermediate: [source, target],
        }

        translator = Translator(linker)
        result: set[str] = translator.translate(sources, source, target, adjacency, {})
        assert result == target_ids

    def test_fallback_connected_uses_es_matches(self) -> None:
        linker = MagicMock()
        source = _uuid()
        target = _uuid()
        sources = {_uuid()}
        third_graph = _uuid()

        connected_id = _uuid()
        target_id = _uuid()

        linker.get_intermediate.side_effect = [
            set(),
            {target_id},
        ]
        linker.get_connected.return_value = {connected_id}

        es_matches = {third_graph: {connected_id}}

        translator = Translator(linker)
        result: set[str] = translator.translate(sources, source, target, {}, es_matches)
        assert target_id in result

    def test_fallback_connected_skips_source_and_target_graphs(self) -> None:
        linker = MagicMock()
        source = _uuid()
        target = _uuid()
        sources = {_uuid()}

        connected_id = _uuid()

        linker.get_intermediate.return_value = set()
        linker.get_connected.return_value = {connected_id}

        es_matches = {
            source: {connected_id},
            target: {connected_id},
        }

        translator = Translator(linker)
        result: set[str] = translator.translate(sources, source, target, {}, es_matches)
        assert result == set()

    def test_fallback_connected_no_overlap_with_es(self) -> None:
        linker = MagicMock()
        source = _uuid()
        target = _uuid()
        sources = {_uuid()}
        third_graph = _uuid()

        linker.get_intermediate.return_value = set()
        linker.get_connected.return_value = {_uuid()}
        es_matches = {third_graph: {_uuid()}}

        translator = Translator(linker)
        result: set[str] = translator.translate(sources, source, target, {}, es_matches)
        assert result == set()

    def test_fallback_connected_empty(self) -> None:
        linker = MagicMock()
        source = _uuid()
        target = _uuid()
        sources = {_uuid()}

        linker.get_intermediate.return_value = set()
        linker.get_connected.return_value = set()

        translator = Translator(linker)
        result: set[str] = translator.translate(sources, source, target, {}, {_uuid(): {_uuid()}})
        assert result == set()

    def test_multihop_multiple_intermediates_first_empty_second_finds(self) -> None:
        linker = MagicMock()
        source = _uuid()
        target = _uuid()
        int_a = _uuid()
        int_b = _uuid()
        sources = {_uuid()}
        target_b = {_uuid()}

        linker.get_intermediate.side_effect = [
            set(),
            set(),
            {_uuid()},
            target_b,
        ]
        linker.get_connected.return_value = set()

        adjacency = {
            source: [int_a, int_b],
            int_a: [target],
            int_b: [target],
        }

        translator = Translator(linker)
        result: set[str] = translator.translate(sources, source, target, adjacency, {})
        assert result == target_b

    def test_multihop_first_intermediate_succeeds_continues_to_second(self) -> None:
        linker = MagicMock()
        source = _uuid()
        target = _uuid()
        int_a = _uuid()
        int_b = _uuid()
        sources = {_uuid()}
        target_a = {_uuid()}
        target_b = {_uuid()}

        linker.get_intermediate.side_effect = [
            set(),
            {_uuid()},
            target_a,
            {_uuid()},
            target_b,
        ]
        linker.get_connected.return_value = set()

        adjacency = {
            source: [int_a, int_b],
            int_a: [target],
            int_b: [target],
        }

        translator = Translator(linker)
        result: set[str] = translator.translate(sources, source, target, adjacency, {})
        assert result == target_a | target_b

    def test_empty_sources_direct_link(self) -> None:
        linker = MagicMock()
        linker.get_intermediate.return_value = set()
        linker.get_connected.return_value = set()

        translator = Translator(linker)
        result: set[str] = translator.translate(set(), _uuid(), _uuid(), {}, {})
        assert result == set()

    def test_empty_adjacency_falls_to_connected(self) -> None:
        linker = MagicMock()
        source = _uuid()
        target = _uuid()
        sources = {_uuid()}
        third = _uuid()
        connected = _uuid()
        final = _uuid()

        linker.get_intermediate.side_effect = [set(), {final}]
        linker.get_connected.return_value = {connected}

        translator = Translator(linker)
        result: set[str] = translator.translate(
            sources, source, target, {}, {third: {connected}},
        )
        assert final in result

    def test_multihop_aggregates_across_intermediates(self) -> None:
        linker = MagicMock()
        source = _uuid()
        target = _uuid()
        int_a = _uuid()
        int_b = _uuid()
        sources = {_uuid()}
        target_a = {_uuid()}
        target_b = {_uuid()}

        linker.get_intermediate.side_effect = [
            set(),
            {_uuid()},
            target_a,
            {_uuid()},
            target_b,
        ]
        linker.get_connected.return_value = set()

        adjacency = {
            source: [int_a, int_b],
            int_a: [target],
            int_b: [target],
        }

        translator = Translator(linker)
        result: set[str] = translator.translate(sources, source, target, adjacency, {})
        assert result == target_a | target_b

    def test_same_graph_returns_exact_sources_reference(self) -> None:
        linker = MagicMock()
        translator = Translator(linker)
        graph = _uuid()
        sources = {_uuid(), _uuid(), _uuid()}

        result: set[str] = translator.translate(sources, graph, graph, {}, {})
        assert result is sources

    def test_fallback_connected_multiple_es_graph_matches(self) -> None:
        linker = MagicMock()
        source = _uuid()
        target = _uuid()
        sources = {_uuid()}
        graph_a = _uuid()
        graph_b = _uuid()

        connected = {_uuid(), _uuid(), _uuid()}
        match_a = {list(connected)[0]}
        match_b = {list(connected)[1]}
        target_from_a = {_uuid()}
        target_from_b = {_uuid()}

        linker.get_intermediate.side_effect = [
            set(),
            target_from_a,
            target_from_b,
        ]
        linker.get_connected.return_value = connected

        es_matches = {
            graph_a: match_a,
            graph_b: match_b,
        }

        translator = Translator(linker)
        result: set[str] = translator.translate(sources, source, target, {}, es_matches)
        assert result == target_from_a | target_from_b
