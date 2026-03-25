from __future__ import annotations

from bcap.search_components.cross_model_advanced_search import (
    MatchType,
    SectionFilter,
)
from helper import _uuid


class TestSectionFilterCreate:
    def test_empty(self) -> None:
        sf = SectionFilter.create({})
        assert sf.graph is None
        assert sf.groups == []

    def test_with_graph_and_groups(self) -> None:
        graph_id = _uuid()
        sf = SectionFilter.create({
            "graph_id": graph_id,
            "groups": [
                {"cards": [], "match": "all", "operator_after": "and"},
                {"cards": [], "match": "any", "operator_after": "or"},
            ],
        })
        assert sf.graph == graph_id
        assert len(sf.groups) == 2
        assert sf.groups[0].match_type == MatchType.ALL
        assert sf.groups[1].match_type == MatchType.ANY

    def test_missing_graph_id(self) -> None:
        sf = SectionFilter.create({"groups": [{"cards": []}]})
        assert sf.graph is None
        assert len(sf.groups) == 1

    def test_missing_groups(self) -> None:
        sf = SectionFilter.create({"graph_id": _uuid()})
        assert sf.groups == []

    def test_empty_groups_list(self) -> None:
        sf = SectionFilter.create({"graph_id": _uuid(), "groups": []})
        assert sf.groups == []
