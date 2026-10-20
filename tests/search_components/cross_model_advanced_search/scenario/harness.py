from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

from typing_extensions import Any

from bcap.search_components.cross_model_advanced_search import (
    Intersector,
    Translator,
)


@dataclass
class Scenario:
    adjacency: dict[str, list[str]] = field(default_factory=dict)
    es_matches: dict[str, set[str]] = field(default_factory=dict)
    expected: set[str] = field(default_factory=set)
    graphs: dict[str, set[str]] = field(default_factory=dict)
    name: str = ""
    operation: str = "intersect"
    relationships: set[tuple[str, str]] = field(default_factory=set)
    target_graph: str = ""


class SyntheticLinker:
    def __init__(
        self,
        graphs: dict[str, set[str]],
        relationships: set[tuple[str, str]],
    ) -> None:
        self._graphs = graphs
        self._relationships = relationships

    def _peers(self, resource_id: str) -> set[str]:
        result = set()

        for a, b in self._relationships:
            if a == resource_id:
                result.add(b)

            if b == resource_id:
                result.add(a)

        return result

    def _connected_in_graph(self, sources: set[str], target_graph: str) -> set[str]:
        target_resources = self._graphs.get(target_graph, set())

        return {
            peer
            for source_id in sources
            for peer in self._peers(source_id)
            if peer in target_resources
        }

    def get_connected(self, sources: set[str]) -> set[str]:
        return {peer for source_id in sources for peer in self._peers(source_id)}

    def get_intermediate(
        self, sources: set[str], source_graph: str, target_graph: str
    ) -> set[str]:
        if source_graph == target_graph:
            return set(sources)

        if not sources:
            return set()

        return self._connected_in_graph(sources, target_graph)

    def get_linked_from_tiles(
        self,
        _source_ids: set[str],
        _source_graph: str,
        _target_graph: str,
        _nodegroup_ids: set[str],
        _tile_filters: dict[str, Any] | None = None,
    ) -> dict[str, set[str]]:
        return defaultdict(set)


def run(scenario: Scenario) -> set[str]:
    linker = SyntheticLinker(scenario.graphs, scenario.relationships)

    intersector = Intersector(
        factory=MagicMock(),
        linker=linker,
        nodes={},
        request=MagicMock(),
        scroller=MagicMock(),
    )
    intersector._translator = Translator(linker)

    def _mock_execute_section(section: Any) -> set[str]:
        return set(scenario.es_matches.get(section.graph, set()))

    def _mock_build_adjacency(
        _sections: Any, _target_graph: str
    ) -> dict[str, list[str]]:
        return scenario.adjacency

    section_data = [{"graph_id": g, "groups": []} for g in scenario.es_matches]

    with (
        patch.object(
            intersector, "_build_adjacency", side_effect=_mock_build_adjacency
        ),
        patch.object(
            intersector, "_execute_section", side_effect=_mock_execute_section
        ),
        patch.object(intersector, "_has_correlated_pairs", return_value=False),
    ):
        return intersector.compute(
            section_data, scenario.target_graph, scenario.operation
        )
