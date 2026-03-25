from __future__ import annotations

from unittest.mock import MagicMock, patch

from typing_extensions import Any

from bcap.search_components.cross_model_advanced_search import (
    CardFilter,
    GroupFilter,
    Intersector,
    SectionFilter,
)
from helper import _make_bool, _uuid


class TestIntersector:
    def _make_intersector(
        self,
        factory: Any = None,
        linker: Any = None,
        nodes: dict | None = None,
        request: Any = None,
        scroller: Any = None,
    ) -> Intersector:
        return Intersector(
            factory=factory or MagicMock(),
            linker=linker or MagicMock(),
            nodes=nodes or {},
            request=request or MagicMock(),
            scroller=scroller or MagicMock(),
        )

    def test_compute_empty_sections(self) -> None:
        inter = self._make_intersector()
        result: set[str] = inter.compute([], _uuid())
        assert result == set()

    @patch.object(Intersector, "_run_es_queries")
    @patch.object(Intersector, "_build_adjacency")
    @patch.object(Intersector, "_translate_to_target")
    @patch.object(Intersector, "_has_correlated_pairs")
    def test_compute_early_exit_on_empty_graph_intersect(
        self,
        mock_has_corr: MagicMock,
        mock_translate: MagicMock,
        mock_adjacency: MagicMock,
        mock_es_queries: MagicMock,
    ) -> None:
        inter = self._make_intersector()
        graph_a = _uuid()
        graph_b = _uuid()

        mock_es_queries.return_value = {graph_a: {_uuid()}, graph_b: set()}

        result: set[str] = inter.compute(
            [{"graph_id": graph_a, "groups": []}, {"graph_id": graph_b, "groups": []}],
            _uuid(),
            "intersect",
        )
        assert result == set()
        mock_translate.assert_not_called()

    @patch.object(Intersector, "_run_es_queries")
    @patch.object(Intersector, "_build_adjacency")
    @patch.object(Intersector, "_translate_to_target")
    @patch.object(Intersector, "_has_correlated_pairs")
    def test_compute_union_does_not_early_exit_on_empty_graph(
        self,
        mock_has_corr: MagicMock,
        mock_translate: MagicMock,
        mock_adjacency: MagicMock,
        mock_es_queries: MagicMock,
    ) -> None:
        inter = self._make_intersector()
        graph_a = _uuid()
        graph_b = _uuid()
        target = _uuid()
        expected = {_uuid()}

        mock_es_queries.return_value = {graph_a: {_uuid()}, graph_b: set()}
        mock_has_corr.return_value = False
        mock_adjacency.return_value = {}
        mock_translate.return_value = expected

        result: set[str] = inter.compute(
            [{"graph_id": graph_a, "groups": []}, {"graph_id": graph_b, "groups": []}],
            target,
            "union",
        )
        mock_translate.assert_called_once()

    @patch.object(Intersector, "_run_es_queries")
    @patch.object(Intersector, "_build_adjacency")
    @patch.object(Intersector, "_translate_to_target")
    @patch.object(Intersector, "_has_correlated_pairs")
    @patch.object(Intersector, "_apply_correlated_filtering")
    def test_compute_correlated_filtering_returns_none_intersect(
        self,
        mock_apply_corr: MagicMock,
        mock_has_corr: MagicMock,
        mock_translate: MagicMock,
        mock_adjacency: MagicMock,
        mock_es_queries: MagicMock,
    ) -> None:
        inter = self._make_intersector()
        graph_a = _uuid()
        graph_b = _uuid()

        mock_es_queries.return_value = {graph_a: {_uuid()}, graph_b: {_uuid()}}
        mock_has_corr.return_value = True
        mock_apply_corr.return_value = None

        result: set[str] = inter.compute(
            [{"graph_id": graph_a, "groups": []}, {"graph_id": graph_b, "groups": []}],
            _uuid(),
            "intersect",
        )
        assert result == set()
        mock_translate.assert_not_called()

    @patch.object(Intersector, "_run_es_queries")
    @patch.object(Intersector, "_build_adjacency")
    @patch.object(Intersector, "_translate_to_target")
    @patch.object(Intersector, "_has_correlated_pairs")
    @patch.object(Intersector, "_apply_correlated_filtering")
    def test_compute_correlated_filtering_empties_one_graph_intersect(
        self,
        mock_apply_corr: MagicMock,
        mock_has_corr: MagicMock,
        mock_translate: MagicMock,
        mock_adjacency: MagicMock,
        mock_es_queries: MagicMock,
    ) -> None:
        inter = self._make_intersector()
        graph_a = _uuid()
        graph_b = _uuid()

        mock_es_queries.return_value = {graph_a: {_uuid()}, graph_b: {_uuid()}}
        mock_has_corr.return_value = True
        mock_apply_corr.return_value = {graph_a: {_uuid()}, graph_b: set()}

        result: set[str] = inter.compute(
            [{"graph_id": graph_a, "groups": []}, {"graph_id": graph_b, "groups": []}],
            _uuid(),
            "intersect",
        )
        assert result == set()
        mock_translate.assert_not_called()

    @patch.object(Intersector, "_run_es_queries")
    @patch.object(Intersector, "_build_adjacency")
    @patch.object(Intersector, "_translate_to_target")
    @patch.object(Intersector, "_has_correlated_pairs")
    def test_compute_single_section_no_correlated_check(
        self,
        mock_has_corr: MagicMock,
        mock_translate: MagicMock,
        mock_adjacency: MagicMock,
        mock_es_queries: MagicMock,
    ) -> None:
        inter = self._make_intersector()
        graph = _uuid()
        target = _uuid()
        expected = {_uuid()}

        mock_es_queries.return_value = {graph: {_uuid()}}
        mock_adjacency.return_value = {}
        mock_translate.return_value = expected

        result: set[str] = inter.compute(
            [{"graph_id": graph, "groups": []}],
            target,
        )
        mock_has_corr.assert_not_called()


class TestIntersectorRunGraphQueries:
    def _make_intersector(self) -> Intersector:
        return Intersector(
            factory=MagicMock(),
            linker=MagicMock(),
            nodes={},
            request=MagicMock(),
            scroller=MagicMock(),
        )

    def test_run_graph_queries_single_section(self) -> None:
        inter = self._make_intersector()
        expected = {_uuid(), _uuid()}

        with patch.object(inter, "_execute_section") as mock_exec:
            mock_exec.return_value = expected
            result: set[str] = inter._run_graph_queries([MagicMock()])

        assert result == expected

    def test_run_graph_queries_second_empty_exits_early(self) -> None:
        inter = self._make_intersector()

        with patch.object(inter, "_execute_section") as mock_exec:
            mock_exec.side_effect = [{_uuid()}, set()]
            result: set[str] = inter._run_graph_queries([MagicMock(), MagicMock()])

        assert result == set()

    def test_run_graph_queries_intersection_of_two(self) -> None:
        inter = self._make_intersector()
        shared = _uuid()
        set_a = {shared, _uuid()}
        set_b = {shared, _uuid()}

        with patch.object(inter, "_execute_section") as mock_exec:
            mock_exec.side_effect = [set_a, set_b]
            result: set[str] = inter._run_graph_queries([MagicMock(), MagicMock()])

        assert result == {shared}

    def test_run_graph_queries_three_sections_no_overlap(self) -> None:
        inter = self._make_intersector()

        with patch.object(inter, "_execute_section") as mock_exec:
            mock_exec.side_effect = [{_uuid()}, {_uuid()}, {_uuid()}]
            result: set[str] = inter._run_graph_queries(
                [MagicMock(), MagicMock(), MagicMock()],
            )

        assert result == set()

    def test_run_graph_queries_empty_list(self) -> None:
        inter = self._make_intersector()

        with patch.object(inter, "_execute_section") as mock_exec:
            result: set[str] = inter._run_graph_queries([])

        mock_exec.assert_not_called()


class TestIntersectorExecuteSection:
    def _make_intersector(self) -> Intersector:
        return Intersector(
            factory=MagicMock(),
            linker=MagicMock(),
            nodes={},
            request=MagicMock(),
            scroller=MagicMock(),
        )

    def test_section_without_graph_returns_empty(self) -> None:
        inter = self._make_intersector()
        section = SectionFilter(graph=None, groups=[])
        result: set[str] = inter._execute_section(section)
        assert result == set()

    @patch("bcap.search_components.cross_model_advanced_search.has_clause")
    def test_section_query_no_clauses_returns_empty(self, mock_has: MagicMock) -> None:
        inter = self._make_intersector()
        mock_has.return_value = False

        section = MagicMock()
        section.graph = _uuid()
        section.build.return_value = _make_bool()

        result: set[str] = inter._execute_section(section)
        assert result == set()
        inter._scroller.ids.assert_not_called()

    @patch("bcap.search_components.cross_model_advanced_search.has_clause")
    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.Terms")
    def test_section_delegates_to_scroller(
        self,
        mock_terms: MagicMock,
        mock_bool_cls: MagicMock,
        mock_has: MagicMock,
    ) -> None:
        scroller = MagicMock()
        expected = {_uuid(), _uuid()}
        scroller.ids.return_value = expected

        inter = Intersector(
            factory=MagicMock(),
            linker=MagicMock(),
            nodes={},
            request=MagicMock(),
            scroller=scroller,
        )
        mock_has.return_value = True
        mock_bool_cls.return_value = _make_bool()

        section = MagicMock()
        section.graph = _uuid()
        section.build.return_value = _make_bool(must=[{"term": {"x": "y"}}])

        result: set[str] = inter._execute_section(section)
        assert result == expected
        scroller.ids.assert_called_once()


class TestIntersectorHasCorrelatedPairs:
    def _make_intersector(self) -> Intersector:
        return Intersector(
            factory=MagicMock(),
            linker=MagicMock(),
            nodes={},
            request=MagicMock(),
            scroller=MagicMock(),
        )

    def test_false_when_no_links(self) -> None:
        inter = self._make_intersector()

        with patch.object(inter, "_find_correlated_nodegroups", return_value=set()):
            result: bool = inter._has_correlated_pairs(
                {_uuid(), _uuid()},
                {_uuid(): MagicMock(), _uuid(): MagicMock()},
            )

        assert result is False

    def test_true_when_links_found(self) -> None:
        inter = self._make_intersector()

        graph_a = _uuid()
        graph_b = _uuid()

        def _mock_find(source: str, target: str, section: Any) -> set[str]:
            if source == graph_a and target == graph_b:
                return {_uuid()}
            return set()

        with patch.object(inter, "_find_correlated_nodegroups", side_effect=_mock_find):
            result: bool = inter._has_correlated_pairs(
                {graph_a, graph_b},
                {graph_a: MagicMock(), graph_b: MagicMock()},
            )

        assert result is True

    def test_missing_section_skipped(self) -> None:
        inter = self._make_intersector()

        graph_a = _uuid()
        graph_b = _uuid()

        with patch.object(inter, "_find_correlated_nodegroups", return_value=set()):
            result: bool = inter._has_correlated_pairs(
                {graph_a, graph_b},
                {graph_a: MagicMock()},
            )

        assert result is False

    def test_single_graph_no_pairs(self) -> None:
        inter = self._make_intersector()

        graph = _uuid()

        with patch.object(inter, "_find_correlated_nodegroups") as mock_find:
            result: bool = inter._has_correlated_pairs(
                {graph},
                {graph: MagicMock()},
            )

        assert result is False
        mock_find.assert_not_called()

    def test_three_graphs_finds_one_pair(self) -> None:
        inter = self._make_intersector()

        graph_a = _uuid()
        graph_b = _uuid()
        graph_c = _uuid()

        def _mock_find(source: str, target: str, section: Any) -> set[str]:
            if source == graph_b and target == graph_c:
                return {_uuid()}
            return set()

        with patch.object(inter, "_find_correlated_nodegroups", side_effect=_mock_find):
            result: bool = inter._has_correlated_pairs(
                {graph_a, graph_b, graph_c},
                {graph_a: MagicMock(), graph_b: MagicMock(), graph_c: MagicMock()},
            )

        assert result is True


class TestIntersectorGetFiltersForNodegroups:
    def _make_intersector(self) -> Intersector:
        return Intersector(
            factory=MagicMock(),
            linker=MagicMock(),
            nodes={},
            request=MagicMock(),
            scroller=MagicMock(),
        )

    def test_matching_nodegroup(self) -> None:
        inter = self._make_intersector()

        ng = _uuid()
        node_id = _uuid()

        card = CardFilter(
            filters={node_id: {"op": "eq", "val": "test"}},
            nodegroup=ng,
        )
        group = GroupFilter(cards=[card])
        section = SectionFilter(graph=_uuid(), groups=[group])

        result: dict[str, Any] = inter._get_filters_for_nodegroups(section, {ng})
        assert node_id in result

    def test_no_matching_nodegroup(self) -> None:
        inter = self._make_intersector()

        ng = _uuid()
        other_ng = _uuid()

        card = CardFilter(
            filters={_uuid(): {"op": "eq", "val": "test"}},
            nodegroup=other_ng,
        )
        group = GroupFilter(cards=[card])
        section = SectionFilter(graph=_uuid(), groups=[group])

        result: dict[str, Any] = inter._get_filters_for_nodegroups(section, {ng})
        assert result == {}

    def test_multiple_cards_same_nodegroup_merged(self) -> None:
        inter = self._make_intersector()

        ng = _uuid()
        node_a = _uuid()
        node_b = _uuid()

        card_a = CardFilter(
            filters={node_a: {"op": "eq", "val": "a"}},
            nodegroup=ng,
        )
        card_b = CardFilter(
            filters={node_b: {"op": "gt", "val": 5}},
            nodegroup=ng,
        )
        group = GroupFilter(cards=[card_a, card_b])
        section = SectionFilter(graph=_uuid(), groups=[group])

        result: dict[str, Any] = inter._get_filters_for_nodegroups(section, {ng})
        assert node_a in result
        assert node_b in result

    def test_empty_groups(self) -> None:
        inter = self._make_intersector()
        section = SectionFilter(graph=_uuid(), groups=[])

        result: dict[str, Any] = inter._get_filters_for_nodegroups(section, {_uuid()})
        assert result == {}

    def test_card_without_nodegroup_skipped(self) -> None:
        inter = self._make_intersector()
        ng = _uuid()

        card = CardFilter(
            filters={_uuid(): {"op": "eq", "val": "x"}},
            nodegroup=None,
        )
        group = GroupFilter(cards=[card])
        section = SectionFilter(graph=_uuid(), groups=[group])

        result: dict[str, Any] = inter._get_filters_for_nodegroups(section, {ng})
        assert result == {}


class TestIntersectorApplyCorrelatedFiltering:
    def _make_intersector(self) -> Intersector:
        linker = MagicMock()
        return Intersector(
            factory=MagicMock(),
            linker=linker,
            nodes={},
            request=MagicMock(),
            scroller=MagicMock(),
        )

    def test_no_correlated_pairs(self) -> None:
        inter = self._make_intersector()
        graph_a = _uuid()
        graph_b = _uuid()

        es_matches: dict[str, set[str]] = {graph_a: {_uuid()}, graph_b: {_uuid()}}
        section_lookup: dict[str, SectionFilter] = {
            graph_a: SectionFilter(graph=graph_a, groups=[]),
            graph_b: SectionFilter(graph=graph_b, groups=[]),
        }

        with patch.object(inter, "_find_correlated_nodegroups", return_value=set()):
            result = inter._apply_correlated_filtering(es_matches, section_lookup, "intersect")

        assert result == es_matches

    def test_correlated_no_overlap_intersect_returns_none(self) -> None:
        inter = self._make_intersector()
        graph_a = _uuid()
        graph_b = _uuid()
        ng = _uuid()

        source_id = _uuid()
        linked_id = _uuid()
        es_b_id = _uuid()

        es_matches: dict[str, set[str]] = {graph_a: {source_id}, graph_b: {es_b_id}}
        section_lookup: dict[str, SectionFilter] = {
            graph_a: SectionFilter(graph=graph_a, groups=[]),
            graph_b: SectionFilter(graph=graph_b, groups=[]),
        }

        def mock_find(source: str, target: str, section: SectionFilter) -> set[str]:
            if source == graph_a and target == graph_b:
                return {ng}
            return set()

        inter._linker.get_linked_from_tiles.return_value = {source_id: {linked_id}}

        with patch.object(inter, "_find_correlated_nodegroups", side_effect=mock_find):
            with patch.object(inter, "_get_filters_for_nodegroups", return_value={}):
                result = inter._apply_correlated_filtering(es_matches, section_lookup, "intersect")

        assert result is None


class TestIntersectorTranslateToTarget:
    def _make_intersector(self) -> Intersector:
        return Intersector(
            factory=MagicMock(),
            linker=MagicMock(),
            nodes={},
            request=MagicMock(),
            scroller=MagicMock(),
        )

    def test_target_graph_in_es_matches(self) -> None:
        inter = self._make_intersector()
        target = _uuid()
        target_ids = {_uuid(), _uuid()}

        with patch.object(inter, "_translate_graph"):
            result: set[str] = inter._translate_to_target(
                {target: target_ids},
                target,
                {},
                "intersect",
            )

        assert result == target_ids

    def test_no_graphs_to_translate(self) -> None:
        inter = self._make_intersector()
        target = _uuid()
        target_ids = {_uuid()}

        result: set[str] = inter._translate_to_target(
            {target: target_ids},
            target,
            {},
            "intersect",
        )
        assert result == target_ids

    def test_intersect_with_no_target_graph_match(self) -> None:
        inter = self._make_intersector()
        target = _uuid()
        source = _uuid()
        translated = {_uuid()}

        with patch.object(inter, "_translate_graph", return_value=translated):
            result: set[str] = inter._translate_to_target(
                {source: {_uuid()}},
                target,
                {},
                "intersect",
            )

        assert result == translated

    def test_union_combines_target_and_translated(self) -> None:
        inter = self._make_intersector()
        target = _uuid()
        source = _uuid()
        target_ids = {_uuid()}
        translated = {_uuid()}

        with patch.object(inter, "_translate_graph", return_value=translated):
            result: set[str] = inter._translate_to_target(
                {target: target_ids, source: {_uuid()}},
                target,
                {},
                "union",
            )

        assert result == target_ids | translated

    def test_intersect_multiple_sources_intersection(self) -> None:
        inter = self._make_intersector()
        target = _uuid()
        source_a = _uuid()
        source_b = _uuid()
        shared = _uuid()

        with patch.object(inter, "_translate_graph") as mock_translate:
            mock_translate.side_effect = [{shared, _uuid()}, {shared, _uuid()}]
            result: set[str] = inter._translate_to_target(
                {source_a: {_uuid()}, source_b: {_uuid()}},
                target,
                {},
                "intersect",
            )

        assert result == {shared}

    def test_intersect_source_translates_to_empty(self) -> None:
        inter = self._make_intersector()
        target = _uuid()
        source = _uuid()

        with patch.object(inter, "_translate_graph", return_value=set()):
            result: set[str] = inter._translate_to_target(
                {source: {_uuid()}},
                target,
                {},
                "intersect",
            )

        assert result == set()


class TestIntersectorFindCorrelatedNodegroups:
    def _make_intersector(self, nodes: dict | None = None) -> Intersector:
        return Intersector(
            factory=MagicMock(),
            linker=MagicMock(),
            nodes=nodes or {},
            request=MagicMock(),
            scroller=MagicMock(),
        )

    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    def test_no_constrained_links(self, mock_cache: MagicMock) -> None:
        mock_cache.get_constrained.return_value = []

        inter = self._make_intersector()
        section = SectionFilter(graph=_uuid(), groups=[])

        result: set[str] = inter._find_correlated_nodegroups(_uuid(), _uuid(), section)
        assert result == set()

    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    def test_no_child_nodegroups(self, mock_cache: MagicMock) -> None:
        ng = _uuid()
        mock_cache.get_constrained.return_value = [{"node": _uuid(), "nodegroup": ng}]
        mock_cache.is_child_nodegroup.return_value = False

        inter = self._make_intersector()
        section = SectionFilter(graph=_uuid(), groups=[])

        result: set[str] = inter._find_correlated_nodegroups(_uuid(), _uuid(), section)
        assert result == set()

    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    def test_child_nodegroup_with_contextual_filter(self, mock_cache: MagicMock) -> None:
        ng = _uuid()
        node_id = _uuid()
        context_node = _uuid()

        mock_cache.get_constrained.return_value = [{"node": node_id, "nodegroup": ng}]
        mock_cache.is_child_nodegroup.return_value = True

        context_node_obj = MagicMock()
        context_node_obj.datatype = "string"

        inter = self._make_intersector(nodes={context_node: context_node_obj})
        card = CardFilter(
            filters={context_node: {"op": "eq", "val": "test"}},
            nodegroup=ng,
        )
        group = GroupFilter(cards=[card])
        section = SectionFilter(graph=_uuid(), groups=[group])

        result: set[str] = inter._find_correlated_nodegroups(_uuid(), _uuid(), section)
        assert ng in result

    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    def test_resource_instance_only_not_contextual(self, mock_cache: MagicMock) -> None:
        ng = _uuid()
        ri_node = _uuid()

        mock_cache.get_constrained.return_value = [{"node": ri_node, "nodegroup": ng}]
        mock_cache.is_child_nodegroup.return_value = True

        ri_node_obj = MagicMock()
        ri_node_obj.datatype = "resource-instance"

        inter = self._make_intersector(nodes={ri_node: ri_node_obj})
        card = CardFilter(
            filters={ri_node: {"val": [{"resourceId": "abc"}]}},
            nodegroup=ng,
        )
        group = GroupFilter(cards=[card])
        section = SectionFilter(graph=_uuid(), groups=[group])

        result: set[str] = inter._find_correlated_nodegroups(_uuid(), _uuid(), section)
        assert result == set()

    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    def test_empty_val_not_contextual(self, mock_cache: MagicMock) -> None:
        ng = _uuid()
        node_id = _uuid()

        mock_cache.get_constrained.return_value = [{"node": _uuid(), "nodegroup": ng}]
        mock_cache.is_child_nodegroup.return_value = True

        inter = self._make_intersector()
        card = CardFilter(
            filters={node_id: {"op": "eq", "val": ""}},
            nodegroup=ng,
        )
        group = GroupFilter(cards=[card])
        section = SectionFilter(graph=_uuid(), groups=[group])

        result: set[str] = inter._find_correlated_nodegroups(_uuid(), _uuid(), section)
        assert result == set()

    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    def test_card_wrong_nodegroup_skipped(self, mock_cache: MagicMock) -> None:
        ng = _uuid()
        other_ng = _uuid()

        mock_cache.get_constrained.return_value = [{"node": _uuid(), "nodegroup": ng}]
        mock_cache.is_child_nodegroup.return_value = True

        inter = self._make_intersector()
        card = CardFilter(
            filters={_uuid(): {"op": "eq", "val": "test"}},
            nodegroup=other_ng,
        )
        group = GroupFilter(cards=[card])
        section = SectionFilter(graph=_uuid(), groups=[group])

        result: set[str] = inter._find_correlated_nodegroups(_uuid(), _uuid(), section)
        assert result == set()

    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    def test_multiple_constrained_links_different_nodegroups(self, mock_cache: MagicMock) -> None:
        ng_a = _uuid()
        ng_b = _uuid()
        context_node_a = _uuid()
        context_node_b = _uuid()

        mock_cache.get_constrained.return_value = [
            {"node": _uuid(), "nodegroup": ng_a},
            {"node": _uuid(), "nodegroup": ng_b},
        ]
        mock_cache.is_child_nodegroup.return_value = True

        node_a_obj = MagicMock()
        node_a_obj.datatype = "string"
        node_b_obj = MagicMock()
        node_b_obj.datatype = "number"

        inter = self._make_intersector(nodes={
            context_node_a: node_a_obj,
            context_node_b: node_b_obj,
        })

        card_a = CardFilter(
            filters={context_node_a: {"op": "eq", "val": "test"}},
            nodegroup=ng_a,
        )
        card_b = CardFilter(
            filters={context_node_b: {"op": "gt", "val": 5}},
            nodegroup=ng_b,
        )
        group = GroupFilter(cards=[card_a, card_b])
        section = SectionFilter(graph=_uuid(), groups=[group])

        result: set[str] = inter._find_correlated_nodegroups(_uuid(), _uuid(), section)
        assert ng_a in result
        assert ng_b in result

    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    def test_resource_instance_list_also_not_contextual(self, mock_cache: MagicMock) -> None:
        ng = _uuid()
        ri_node = _uuid()

        mock_cache.get_constrained.return_value = [{"node": ri_node, "nodegroup": ng}]
        mock_cache.is_child_nodegroup.return_value = True

        ri_node_obj = MagicMock()
        ri_node_obj.datatype = "resource-instance-list"

        inter = self._make_intersector(nodes={ri_node: ri_node_obj})
        card = CardFilter(
            filters={ri_node: {"val": [{"resourceId": "abc"}]}},
            nodegroup=ng,
        )
        group = GroupFilter(cards=[card])
        section = SectionFilter(graph=_uuid(), groups=[group])

        result: set[str] = inter._find_correlated_nodegroups(_uuid(), _uuid(), section)
        assert result == set()
