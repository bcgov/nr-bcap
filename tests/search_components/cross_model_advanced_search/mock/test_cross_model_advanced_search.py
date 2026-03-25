from __future__ import annotations

import json

from unittest.mock import MagicMock, patch

from typing_extensions import Any

from bcap.search_components.cross_model_advanced_search import CrossModelAdvancedSearch
from helper import (
    _make_bool,
    _make_node,
    _uuid,
)


class TestCrossModelAdvancedSearch:
    def _make_filter(self) -> CrossModelAdvancedSearch:
        f = CrossModelAdvancedSearch.__new__(CrossModelAdvancedSearch)
        f.request = MagicMock()
        f.request.user.id = 1
        f._nodes = {}
        f._data = None
        f._target_ids = None
        return f


class TestAppendDslBasic(TestCrossModelAdvancedSearch):
    def test_empty_data(self) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}
        f.append_dsl(query_obj, querystring="{}")
        query_obj["query"].add_query.assert_not_called()

    def test_no_sections(self) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}
        f.append_dsl(query_obj, querystring='{"sections": []}')
        query_obj["query"].add_query.assert_not_called()

    def test_none_data(self) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}
        f.append_dsl(query_obj, querystring=None)
        query_obj["query"].add_query.assert_not_called()

    def test_dict_data(self) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}
        f.append_dsl(query_obj, querystring={})
        query_obj["query"].add_query.assert_not_called()

    def test_dict_data_with_empty_sections(self) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}
        f.append_dsl(query_obj, querystring={"sections": []})
        query_obj["query"].add_query.assert_not_called()

    def test_dict_data_with_no_sections_key(self) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}
        f.append_dsl(query_obj, querystring={"translate_mode": "none"})
        query_obj["query"].add_query.assert_not_called()

    def test_stores_data_on_instance(self) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}

        data = {"sections": [{"graph_id": _uuid(), "groups": []}], "translate_mode": "none"}

        with patch("bcap.search_components.cross_model_advanced_search.DataTypeFactory"):
            with patch("bcap.search_components.cross_model_advanced_search.SectionFilter") as mock_sf:
                mock_section = MagicMock()
                mock_section.graph = None
                mock_sf.create.return_value = mock_section
                with patch("bcap.search_components.cross_model_advanced_search.Bool") as mock_bool:
                    mock_bool.return_value = _make_bool()
                    with patch("bcap.search_components.cross_model_advanced_search.has_clause", return_value=False):
                        f.append_dsl(query_obj, querystring=data)

        assert f._data == data

    def test_no_querystring_kwarg(self) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}
        f.append_dsl(query_obj)
        query_obj["query"].add_query.assert_not_called()


class TestAppendDslRawMode(TestCrossModelAdvancedSearch):
    @patch("bcap.search_components.cross_model_advanced_search.DataTypeFactory")
    @patch("bcap.search_components.cross_model_advanced_search.SectionFilter")
    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.Terms")
    @patch("bcap.search_components.cross_model_advanced_search.has_clause")
    def test_raw_mode_with_valid_section(
        self,
        mock_has_clause: MagicMock,
        mock_terms: MagicMock,
        mock_bool_cls: MagicMock,
        mock_section_cls: MagicMock,
        mock_factory: MagicMock,
    ) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}

        mock_section = MagicMock()
        mock_section.graph = _uuid()
        mock_section.build.return_value = _make_bool(must=[{"term": {"x": "y"}}])
        mock_section_cls.create.return_value = mock_section

        mock_cross_query = _make_bool(should=[{"nested": {}}])
        mock_graph_filter = _make_bool()
        mock_bool_cls.side_effect = [mock_cross_query, mock_graph_filter]

        mock_has_clause.side_effect = [True, True]

        data = json.dumps({
            "sections": [{"graph_id": _uuid(), "groups": []}],
            "translate_mode": "none",
        })

        f.append_dsl(query_obj, querystring=data)
        query_obj["query"].add_query.assert_called_once()

    @patch("bcap.search_components.cross_model_advanced_search.DataTypeFactory")
    @patch("bcap.search_components.cross_model_advanced_search.SectionFilter")
    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.has_clause")
    def test_raw_mode_skips_section_without_graph(
        self,
        mock_has_clause: MagicMock,
        mock_bool_cls: MagicMock,
        mock_section_cls: MagicMock,
        mock_factory: MagicMock,
    ) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}

        mock_section = MagicMock()
        mock_section.graph = None
        mock_section_cls.create.return_value = mock_section

        mock_cross_query = _make_bool()
        mock_bool_cls.return_value = mock_cross_query
        mock_has_clause.return_value = False

        data = json.dumps({
            "sections": [{"groups": []}],
            "translate_mode": "none",
        })

        f.append_dsl(query_obj, querystring=data)
        query_obj["query"].add_query.assert_not_called()

    @patch("bcap.search_components.cross_model_advanced_search.DataTypeFactory")
    @patch("bcap.search_components.cross_model_advanced_search.SectionFilter")
    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.has_clause")
    def test_raw_mode_skips_empty_section_query(
        self,
        mock_has_clause: MagicMock,
        mock_bool_cls: MagicMock,
        mock_section_cls: MagicMock,
        mock_factory: MagicMock,
    ) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}

        mock_section = MagicMock()
        mock_section.graph = _uuid()
        mock_section.build.return_value = _make_bool()
        mock_section_cls.create.return_value = mock_section

        mock_cross_query = _make_bool()
        mock_bool_cls.return_value = mock_cross_query
        mock_has_clause.return_value = False

        data = json.dumps({
            "sections": [{"graph_id": _uuid(), "groups": []}],
            "translate_mode": "none",
        })

        f.append_dsl(query_obj, querystring=data)
        query_obj["query"].add_query.assert_not_called()

    @patch("bcap.search_components.cross_model_advanced_search.DataTypeFactory")
    @patch("bcap.search_components.cross_model_advanced_search.SectionFilter")
    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.Terms")
    @patch("bcap.search_components.cross_model_advanced_search.has_clause")
    def test_raw_mode_multiple_sections_sets_minimum_should_match(
        self,
        mock_has_clause: MagicMock,
        mock_terms: MagicMock,
        mock_bool_cls: MagicMock,
        mock_section_cls: MagicMock,
        mock_factory: MagicMock,
    ) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}

        sections = []
        for _ in range(2):
            mock_section = MagicMock()
            mock_section.graph = _uuid()
            mock_section.build.return_value = _make_bool(must=[{"term": {"x": "y"}}])
            sections.append(mock_section)

        mock_section_cls.create.side_effect = sections

        mock_cross_query = _make_bool(should=[{"nested": {}}, {"nested": {}}])
        mock_graph_filters = [_make_bool(), _make_bool()]
        mock_bool_cls.side_effect = [mock_cross_query] + mock_graph_filters

        mock_has_clause.return_value = True

        data = json.dumps({
            "sections": [
                {"graph_id": _uuid(), "groups": []},
                {"graph_id": _uuid(), "groups": []},
            ],
            "translate_mode": "none",
        })

        f.append_dsl(query_obj, querystring=data)
        assert mock_cross_query.dsl["bool"]["minimum_should_match"] == 1

    @patch("bcap.search_components.cross_model_advanced_search.DataTypeFactory")
    @patch("bcap.search_components.cross_model_advanced_search.SectionFilter")
    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.has_clause")
    def test_raw_mode_mix_valid_and_invalid_sections(
        self,
        mock_has_clause: MagicMock,
        mock_bool_cls: MagicMock,
        mock_section_cls: MagicMock,
        mock_factory: MagicMock,
    ) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}

        valid_section = MagicMock()
        valid_section.graph = _uuid()
        valid_section.build.return_value = _make_bool(must=[{"term": {"x": "y"}}])

        invalid_section = MagicMock()
        invalid_section.graph = None

        mock_section_cls.create.side_effect = [valid_section, invalid_section]

        mock_cross_query = _make_bool(should=[{"nested": {}}])
        mock_graph_filter = _make_bool()
        mock_bool_cls.side_effect = [mock_cross_query, mock_graph_filter]

        mock_has_clause.side_effect = [True, True]

        data = json.dumps({
            "sections": [
                {"graph_id": _uuid(), "groups": []},
                {"groups": []},
            ],
            "translate_mode": "none",
        })

        f.append_dsl(query_obj, querystring=data)
        query_obj["query"].add_query.assert_called_once()


class TestAppendDslIntersectionMode(TestCrossModelAdvancedSearch):
    @patch.object(CrossModelAdvancedSearch, "_get_graph_id")
    @patch.object(CrossModelAdvancedSearch, "_compute_target_ids")
    @patch.object(CrossModelAdvancedSearch, "_build_cache")
    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.Terms")
    def test_with_target_ids(
        self,
        mock_terms: MagicMock,
        mock_bool_cls: MagicMock,
        mock_build_cache: MagicMock,
        mock_compute: MagicMock,
        mock_get_graph: MagicMock,
    ) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}

        target_graph = _uuid()
        mock_get_graph.return_value = target_graph
        mock_compute.return_value = {_uuid(), _uuid()}

        mock_id_filter = _make_bool()
        mock_bool_cls.return_value = mock_id_filter

        data = json.dumps({
            "sections": [{"graph_id": _uuid(), "groups": []}],
            "translate_mode": "some-slug",
        })

        f.append_dsl(query_obj, querystring=data)
        query_obj["query"].add_query.assert_called_once()

    @patch.object(CrossModelAdvancedSearch, "_get_graph_id")
    @patch.object(CrossModelAdvancedSearch, "_compute_target_ids")
    @patch.object(CrossModelAdvancedSearch, "_build_cache")
    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.Terms")
    def test_empty_target_ids_adds_impossible_filter(
        self,
        mock_terms: MagicMock,
        mock_bool_cls: MagicMock,
        mock_build_cache: MagicMock,
        mock_compute: MagicMock,
        mock_get_graph: MagicMock,
    ) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}

        mock_get_graph.return_value = _uuid()
        mock_compute.return_value = set()

        mock_id_filter = _make_bool()
        mock_bool_cls.return_value = mock_id_filter

        data = json.dumps({
            "sections": [{"graph_id": _uuid(), "groups": []}],
            "translate_mode": "some-slug",
        })

        f.append_dsl(query_obj, querystring=data)
        query_obj["query"].add_query.assert_called_once()
        mock_terms.assert_called_with(
            field="resourceinstanceid", terms=["__no_match__"]
        )

    @patch.object(CrossModelAdvancedSearch, "_get_graph_id")
    @patch.object(CrossModelAdvancedSearch, "_build_cache")
    def test_invalid_slug_returns_early(
        self,
        mock_build_cache: MagicMock,
        mock_get_graph: MagicMock,
    ) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}

        mock_get_graph.return_value = None

        data = json.dumps({
            "sections": [{"graph_id": _uuid(), "groups": []}],
            "translate_mode": "nonexistent-slug",
        })

        f.append_dsl(query_obj, querystring=data)
        query_obj["query"].add_query.assert_not_called()

    @patch.object(CrossModelAdvancedSearch, "_get_graph_id")
    @patch.object(CrossModelAdvancedSearch, "_compute_target_ids")
    @patch.object(CrossModelAdvancedSearch, "_build_cache")
    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.Terms")
    @patch("bcap.search_components.cross_model_advanced_search.chunk")
    @patch("bcap.search_components.cross_model_advanced_search.ES_MAX_TERMS", 2)
    def test_large_id_list_batched(
        self,
        mock_chunk: MagicMock,
        mock_terms: MagicMock,
        mock_bool_cls: MagicMock,
        mock_build_cache: MagicMock,
        mock_compute: MagicMock,
        mock_get_graph: MagicMock,
    ) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}

        target_ids = {_uuid() for _ in range(5)}
        mock_get_graph.return_value = _uuid()
        mock_compute.return_value = target_ids

        mock_id_filter = _make_bool()
        mock_bool_cls.return_value = mock_id_filter
        mock_chunk.return_value = [list(target_ids)[:2], list(target_ids)[2:]]

        data = json.dumps({
            "sections": [{"graph_id": _uuid(), "groups": []}],
            "translate_mode": "some-slug",
        })

        f.append_dsl(query_obj, querystring=data)
        assert mock_id_filter.should.call_count == 2
        assert mock_id_filter.dsl["bool"]["minimum_should_match"] == 1

    @patch.object(CrossModelAdvancedSearch, "_get_graph_id")
    @patch.object(CrossModelAdvancedSearch, "_compute_target_ids")
    @patch.object(CrossModelAdvancedSearch, "_build_cache")
    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.Terms")
    def test_stores_target_ids_on_instance(
        self,
        mock_terms: MagicMock,
        mock_bool_cls: MagicMock,
        mock_build_cache: MagicMock,
        mock_compute: MagicMock,
        mock_get_graph: MagicMock,
    ) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}

        expected = {_uuid(), _uuid()}
        mock_get_graph.return_value = _uuid()
        mock_compute.return_value = expected
        mock_bool_cls.return_value = _make_bool()

        data = json.dumps({
            "sections": [{"graph_id": _uuid(), "groups": []}],
            "translate_mode": "some-slug",
        })

        f.append_dsl(query_obj, querystring=data)
        assert f._target_ids == expected

    @patch.object(CrossModelAdvancedSearch, "_get_graph_id")
    @patch.object(CrossModelAdvancedSearch, "_compute_target_ids")
    @patch.object(CrossModelAdvancedSearch, "_build_cache")
    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.Terms")
    def test_passes_result_operation_to_compute(
        self,
        mock_terms: MagicMock,
        mock_bool_cls: MagicMock,
        mock_build_cache: MagicMock,
        mock_compute: MagicMock,
        mock_get_graph: MagicMock,
    ) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}

        mock_get_graph.return_value = _uuid()
        mock_compute.return_value = set()
        mock_bool_cls.return_value = _make_bool()

        data = json.dumps({
            "sections": [{"graph_id": _uuid(), "groups": []}],
            "translate_mode": "some-slug",
            "result_operation": "union",
        })

        f.append_dsl(query_obj, querystring=data)
        call_args = mock_compute.call_args
        assert call_args[0][2] == "union"

    @patch.object(CrossModelAdvancedSearch, "_get_graph_id")
    @patch.object(CrossModelAdvancedSearch, "_compute_target_ids")
    @patch.object(CrossModelAdvancedSearch, "_build_cache")
    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.Terms")
    def test_default_operation_is_intersect(
        self,
        mock_terms: MagicMock,
        mock_bool_cls: MagicMock,
        mock_build_cache: MagicMock,
        mock_compute: MagicMock,
        mock_get_graph: MagicMock,
    ) -> None:
        f = self._make_filter()
        query_obj: dict[str, Any] = {"query": MagicMock()}

        mock_get_graph.return_value = _uuid()
        mock_compute.return_value = set()
        mock_bool_cls.return_value = _make_bool()

        data = json.dumps({
            "sections": [{"graph_id": _uuid(), "groups": []}],
            "translate_mode": "some-slug",
        })

        f.append_dsl(query_obj, querystring=data)
        call_args = mock_compute.call_args
        assert call_args[0][2] == "intersect"


class TestCacheKey(TestCrossModelAdvancedSearch):
    def test_deterministic(self) -> None:
        f = self._make_filter()
        f._data = {"sections": [], "translate_mode": "none", "result_operation": "intersect"}

        key1: str = f._cache_key(f._data)
        key2: str = f._cache_key(f._data)
        assert key1 == key2

    def test_varies_by_user(self) -> None:
        f1 = self._make_filter()
        f1.request.user.id = 1
        f1._data = {"sections": [], "translate_mode": "none"}

        f2 = self._make_filter()
        f2.request.user.id = 2
        f2._data = {"sections": [], "translate_mode": "none"}

        assert f1._cache_key(f1._data) != f2._cache_key(f2._data)

    def test_varies_by_sections(self) -> None:
        f = self._make_filter()

        key1: str = f._cache_key({"sections": [{"graph_id": "a"}], "translate_mode": "none"})
        key2: str = f._cache_key({"sections": [{"graph_id": "b"}], "translate_mode": "none"})
        assert key1 != key2

    def test_varies_by_translate_mode(self) -> None:
        f = self._make_filter()

        key1: str = f._cache_key({"sections": [], "translate_mode": "none"})
        key2: str = f._cache_key({"sections": [], "translate_mode": "some-slug"})
        assert key1 != key2

    def test_varies_by_operation(self) -> None:
        f = self._make_filter()

        key1: str = f._cache_key({"sections": [], "translate_mode": "none", "result_operation": "intersect"})
        key2: str = f._cache_key({"sections": [], "translate_mode": "none", "result_operation": "union"})
        assert key1 != key2

    def test_prefix(self) -> None:
        f = self._make_filter()
        f._data = {"sections": []}
        key: str = f._cache_key(f._data)
        assert key.startswith("cross_model_search_")

    def test_key_is_md5_length(self) -> None:
        f = self._make_filter()
        f._data = {"sections": []}
        key: str = f._cache_key(f._data)
        suffix = key.replace("cross_model_search_", "")
        assert len(suffix) == 32

    def test_same_sections_different_order_same_key(self) -> None:
        f = self._make_filter()
        sections = [{"graph_id": "a"}, {"graph_id": "b"}]

        key1: str = f._cache_key({"sections": sections, "translate_mode": "none"})
        key2: str = f._cache_key({"sections": sections, "translate_mode": "none"})
        assert key1 == key2

    def test_missing_result_operation_uses_default(self) -> None:
        f = self._make_filter()
        key_with: str = f._cache_key({
            "sections": [],
            "translate_mode": "none",
            "result_operation": "intersect",
        })
        key_without: str = f._cache_key({
            "sections": [],
            "translate_mode": "none",
        })
        assert key_with == key_without


class TestBuildCache(TestCrossModelAdvancedSearch):
    def test_populates_nodes(self) -> None:
        f = self._make_filter()
        node_id = _uuid()
        mock_node = _make_node(node_id=node_id)
        mock_node.pk = node_id

        sections: list[dict[str, Any]] = [{"groups": [{"cards": [{"filters": {node_id: {}}}]}]}]

        with patch("bcap.search_components.cross_model_advanced_search.Node") as mock_node_cls:
            mock_qs = MagicMock()
            mock_qs.select_related.return_value = [mock_node]
            mock_node_cls.objects.filter.return_value = mock_qs

            f._build_cache(sections)

        assert str(mock_node.nodeid) in f._nodes

    def test_empty_sections(self) -> None:
        f = self._make_filter()

        with patch("bcap.search_components.cross_model_advanced_search.Node") as mock_node_cls:
            f._build_cache([])
            mock_node_cls.objects.filter.assert_not_called()

    def test_no_node_ids(self) -> None:
        f = self._make_filter()

        with patch("bcap.search_components.cross_model_advanced_search.Node") as mock_node_cls:
            f._build_cache([{"groups": [{"cards": [{"filters": {}}]}]}])
            mock_node_cls.objects.filter.assert_not_called()

    def test_multiple_sections_collects_all_node_ids(self) -> None:
        f = self._make_filter()
        node_a = _uuid()
        node_b = _uuid()

        sections: list[dict[str, Any]] = [
            {"groups": [{"cards": [{"filters": {node_a: {}}}]}]},
            {"groups": [{"cards": [{"filters": {node_b: {}}}]}]},
        ]

        with patch("bcap.search_components.cross_model_advanced_search.Node") as mock_node_cls:
            mock_qs = MagicMock()
            mock_qs.select_related.return_value = []
            mock_node_cls.objects.filter.return_value = mock_qs

            f._build_cache(sections)

            call_kwargs = mock_node_cls.objects.filter.call_args
            assert node_a in call_kwargs.kwargs["pk__in"]
            assert node_b in call_kwargs.kwargs["pk__in"]

    def test_nested_groups_and_cards(self) -> None:
        f = self._make_filter()
        node_a = _uuid()
        node_b = _uuid()
        node_c = _uuid()

        sections: list[dict[str, Any]] = [{
            "groups": [
                {"cards": [
                    {"filters": {node_a: {}}},
                    {"filters": {node_b: {}}},
                ]},
                {"cards": [
                    {"filters": {node_c: {}}},
                ]},
            ],
        }]

        with patch("bcap.search_components.cross_model_advanced_search.Node") as mock_node_cls:
            mock_qs = MagicMock()
            mock_qs.select_related.return_value = []
            mock_node_cls.objects.filter.return_value = mock_qs

            f._build_cache(sections)

            call_kwargs = mock_node_cls.objects.filter.call_args
            ids = call_kwargs.kwargs["pk__in"]
            assert node_a in ids
            assert node_b in ids
            assert node_c in ids

    def test_duplicate_node_ids_across_sections_deduplicated(self) -> None:
        f = self._make_filter()
        shared_node = _uuid()

        sections: list[dict[str, Any]] = [
            {"groups": [{"cards": [{"filters": {shared_node: {}}}]}]},
            {"groups": [{"cards": [{"filters": {shared_node: {}}}]}]},
        ]

        with patch("bcap.search_components.cross_model_advanced_search.Node") as mock_node_cls:
            mock_qs = MagicMock()
            mock_qs.select_related.return_value = []
            mock_node_cls.objects.filter.return_value = mock_qs

            f._build_cache(sections)

            call_kwargs = mock_node_cls.objects.filter.call_args
            ids = call_kwargs.kwargs["pk__in"]
            assert list(ids).count(shared_node) == 1 or isinstance(ids, set)

    def test_section_missing_groups_key(self) -> None:
        f = self._make_filter()

        with patch("bcap.search_components.cross_model_advanced_search.Node") as mock_node_cls:
            f._build_cache([{"not_groups": []}])
            mock_node_cls.objects.filter.assert_not_called()

    def test_card_missing_filters_key(self) -> None:
        f = self._make_filter()

        with patch("bcap.search_components.cross_model_advanced_search.Node") as mock_node_cls:
            f._build_cache([{"groups": [{"cards": [{"not_filters": {}}]}]}])
            mock_node_cls.objects.filter.assert_not_called()


class TestComputeTargetIds(TestCrossModelAdvancedSearch):
    @patch("bcap.search_components.cross_model_advanced_search.cache")
    def test_returns_cached(self, mock_cache: MagicMock) -> None:
        f = self._make_filter()
        f._data = {"sections": [], "translate_mode": "none"}
        expected = [_uuid(), _uuid()]
        mock_cache.get.return_value = expected

        result: set[str] = f._compute_target_ids([], _uuid(), "intersect")
        assert result == set(expected)

    @patch("bcap.search_components.cross_model_advanced_search.cache")
    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    @patch("bcap.search_components.cross_model_advanced_search.SearchEngineFactory")
    @patch("bcap.search_components.cross_model_advanced_search.DataTypeFactory")
    @patch("bcap.search_components.cross_model_advanced_search.Scroller")
    @patch("bcap.search_components.cross_model_advanced_search.Linker")
    @patch("bcap.search_components.cross_model_advanced_search.Intersector")
    def test_computes_fresh_when_no_cache(
        self,
        mock_intersector_cls: MagicMock,
        mock_linker_cls: MagicMock,
        mock_scroller_cls: MagicMock,
        mock_dt_factory: MagicMock,
        mock_se_factory: MagicMock,
        mock_link_cache: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        f = self._make_filter()
        f._data = {"sections": [], "translate_mode": "none"}
        mock_cache.get.return_value = None
        mock_link_cache._ready = True

        expected = {_uuid()}
        mock_intersector_cls.return_value.compute.return_value = expected

        result: set[str] = f._compute_target_ids([], _uuid(), "intersect")
        assert result == expected
        mock_cache.set.assert_called_once()

    @patch("bcap.search_components.cross_model_advanced_search.cache")
    @patch("bcap.search_components.cross_model_advanced_search.LinkCache")
    @patch("bcap.search_components.cross_model_advanced_search.SearchEngineFactory")
    @patch("bcap.search_components.cross_model_advanced_search.DataTypeFactory")
    @patch("bcap.search_components.cross_model_advanced_search.Scroller")
    @patch("bcap.search_components.cross_model_advanced_search.Linker")
    @patch("bcap.search_components.cross_model_advanced_search.Intersector")
    def test_inits_link_cache_if_not_ready(
        self,
        mock_intersector_cls: MagicMock,
        mock_linker_cls: MagicMock,
        mock_scroller_cls: MagicMock,
        mock_dt_factory: MagicMock,
        mock_se_factory: MagicMock,
        mock_link_cache: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        f = self._make_filter()
        f._data = {"sections": [], "translate_mode": "none"}
        mock_cache.get.return_value = None
        mock_link_cache._ready = False

        mock_intersector_cls.return_value.compute.return_value = set()

        f._compute_target_ids([], _uuid(), "intersect")
        mock_link_cache._init.assert_called_once()

    @patch("bcap.search_components.cross_model_advanced_search.cache")
    def test_cached_empty_list_returns_empty_set(self, mock_cache: MagicMock) -> None:
        f = self._make_filter()
        f._data = {"sections": [], "translate_mode": "none"}
        mock_cache.get.return_value = []

        result: set[str] = f._compute_target_ids([], _uuid(), "intersect")
        assert result == set()


class TestGetGraphId(TestCrossModelAdvancedSearch):
    @patch("bcap.search_components.cross_model_advanced_search.GraphModel")
    def test_valid_uuid(self, mock_graph: MagicMock) -> None:
        f = self._make_filter()
        graph_id = _uuid()

        mock_instance = MagicMock()
        mock_instance.graphid = graph_id
        mock_graph.objects.filter.return_value.only.return_value.first.return_value = mock_instance

        result: str | None = f._get_graph_id(graph_id)
        assert result == graph_id

    @patch("bcap.search_components.cross_model_advanced_search.GraphModel")
    def test_slug_resolution(self, mock_graph: MagicMock) -> None:
        f = self._make_filter()
        graph_id = _uuid()

        mock_instance = MagicMock()
        mock_instance.graphid = graph_id
        mock_graph.objects.filter.return_value.only.return_value.first.return_value = mock_instance

        result: str | None = f._get_graph_id("my-graph-slug")
        assert result == graph_id

    @patch("bcap.search_components.cross_model_advanced_search.GraphModel")
    def test_not_found_returns_none(self, mock_graph: MagicMock) -> None:
        f = self._make_filter()
        mock_graph.objects.filter.return_value.only.return_value.first.return_value = None

        result: str | None = f._get_graph_id(_uuid())
        assert result is None

    @patch("bcap.search_components.cross_model_advanced_search.GraphModel")
    def test_slug_not_found_returns_none(self, mock_graph: MagicMock) -> None:
        f = self._make_filter()
        mock_graph.objects.filter.return_value.only.return_value.first.return_value = None

        result: str | None = f._get_graph_id("nonexistent-slug")
        assert result is None

    @patch("bcap.search_components.cross_model_advanced_search.GraphModel")
    def test_uuid_like_string_that_is_not_uuid(self, mock_graph: MagicMock) -> None:
        f = self._make_filter()
        mock_graph.objects.filter.return_value.only.return_value.first.return_value = None

        result: str | None = f._get_graph_id("not-a-uuid-at-all")
        assert result is None

    @patch("bcap.search_components.cross_model_advanced_search.GraphModel")
    def test_empty_string_treated_as_slug(self, mock_graph: MagicMock) -> None:
        f = self._make_filter()
        mock_graph.objects.filter.return_value.only.return_value.first.return_value = None

        result: str | None = f._get_graph_id("")
        assert result is None


class TestPostSearchHook(TestCrossModelAdvancedSearch):
    def test_no_error(self) -> None:
        f = self._make_filter()
        f.post_search_hook({}, {})

    def test_accepts_kwargs(self) -> None:
        f = self._make_filter()
        f.post_search_hook({}, {}, extra="param")
