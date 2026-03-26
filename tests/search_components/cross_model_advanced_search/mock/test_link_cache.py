from __future__ import annotations

from unittest.mock import MagicMock, patch

from typing_extensions import Any

from bcap.search_components.cross_model_advanced_search import LinkCache
from helper import _uuid


class TestLinkCacheExtractTarget:
    @patch("bcap.search_components.cross_model_advanced_search.Node")
    @patch("bcap.search_components.cross_model_advanced_search.NodeGroup")
    def test_graphid_string(self, mock_ng: MagicMock, mock_node: MagicMock) -> None:
        result: list[str] = LinkCache._extract_target({"graphid": "abc-123"})
        assert result == ["abc-123"]

    @patch("bcap.search_components.cross_model_advanced_search.Node")
    @patch("bcap.search_components.cross_model_advanced_search.NodeGroup")
    def test_graphid_list(self, mock_ng: MagicMock, mock_node: MagicMock) -> None:
        result: list[str] = LinkCache._extract_target({"graphid": ["abc", "def"]})
        assert result == ["abc", "def"]

    @patch("bcap.search_components.cross_model_advanced_search.Node")
    @patch("bcap.search_components.cross_model_advanced_search.NodeGroup")
    def test_graphs_array(self, mock_ng: MagicMock, mock_node: MagicMock) -> None:
        result: list[str] = LinkCache._extract_target(
            {
                "graphs": [
                    {"graphid": "abc"},
                    {"graphid": "def"},
                ],
            }
        )
        assert result == ["abc", "def"]

    @patch("bcap.search_components.cross_model_advanced_search.Node")
    @patch("bcap.search_components.cross_model_advanced_search.NodeGroup")
    def test_empty_config(self, mock_ng: MagicMock, mock_node: MagicMock) -> None:
        result: list[str] = LinkCache._extract_target({})
        assert result == []

    @patch("bcap.search_components.cross_model_advanced_search.Node")
    @patch("bcap.search_components.cross_model_advanced_search.NodeGroup")
    def test_null_graphid(self, mock_ng: MagicMock, mock_node: MagicMock) -> None:
        result: list[str] = LinkCache._extract_target({"graphid": None})
        assert result == []

    @patch("bcap.search_components.cross_model_advanced_search.Node")
    @patch("bcap.search_components.cross_model_advanced_search.NodeGroup")
    def test_both_formats(self, mock_ng: MagicMock, mock_node: MagicMock) -> None:
        result: list[str] = LinkCache._extract_target(
            {
                "graphid": "abc",
                "graphs": [{"graphid": "def"}],
            }
        )
        assert result == ["abc", "def"]

    @patch("bcap.search_components.cross_model_advanced_search.Node")
    @patch("bcap.search_components.cross_model_advanced_search.NodeGroup")
    def test_empty_graphs_list(self, mock_ng: MagicMock, mock_node: MagicMock) -> None:
        result: list[str] = LinkCache._extract_target({"graphs": []})
        assert result == []

    @patch("bcap.search_components.cross_model_advanced_search.Node")
    @patch("bcap.search_components.cross_model_advanced_search.NodeGroup")
    def test_graphs_missing_graphid(
        self, mock_ng: MagicMock, mock_node: MagicMock
    ) -> None:
        result: list[str] = LinkCache._extract_target(
            {
                "graphs": [{"other_key": "val"}],
            }
        )
        assert result == []

    @patch("bcap.search_components.cross_model_advanced_search.Node")
    @patch("bcap.search_components.cross_model_advanced_search.NodeGroup")
    def test_graphid_empty_string(
        self, mock_ng: MagicMock, mock_node: MagicMock
    ) -> None:
        result: list[str] = LinkCache._extract_target({"graphid": ""})
        assert result == []

    @patch("bcap.search_components.cross_model_advanced_search.Node")
    @patch("bcap.search_components.cross_model_advanced_search.NodeGroup")
    def test_graphid_list_with_empty_strings(
        self, mock_ng: MagicMock, mock_node: MagicMock
    ) -> None:
        result: list[str] = LinkCache._extract_target({"graphid": ["", "abc", ""]})
        assert "abc" in result

    @patch("bcap.search_components.cross_model_advanced_search.Node")
    @patch("bcap.search_components.cross_model_advanced_search.NodeGroup")
    def test_graphs_array_with_none_graphid(
        self, mock_ng: MagicMock, mock_node: MagicMock
    ) -> None:
        result: list[str] = LinkCache._extract_target(
            {
                "graphs": [
                    {"graphid": None},
                    {"graphid": "abc"},
                ],
            }
        )
        assert "abc" in result


class TestLinkCacheGetAndCache:
    def setup_method(self) -> None:
        LinkCache.clear()

    def test_get_returns_empty_before_init(self) -> None:
        with patch.object(LinkCache, "_init"):
            LinkCache._ready = True
            LinkCache._cache = {}
            LinkCache._unconstrained = {}
            LinkCache._graph_nodes = {}

            result: list[dict[str, Any]] = LinkCache.get(_uuid(), _uuid())
            assert result == []

    def test_get_constrained_returns_empty_before_init(self) -> None:
        with patch.object(LinkCache, "_init"):
            LinkCache._ready = True
            LinkCache._constrained_cache = {}
            LinkCache._graph_nodes = {}

            result: list[dict[str, Any]] = LinkCache.get_constrained(_uuid(), _uuid())
            assert result == []

    def test_get_caches_result(self) -> None:
        LinkCache._ready = True
        LinkCache._cache = {}
        LinkCache._graph_nodes = {}
        LinkCache._unconstrained = {}

        source = _uuid()
        target = _uuid()

        result1: list[dict[str, Any]] = LinkCache.get(source, target)
        result2: list[dict[str, Any]] = LinkCache.get(source, target)
        assert result1 is result2

    def test_get_constrained_caches_result(self) -> None:
        LinkCache._ready = True
        LinkCache._constrained_cache = {}
        LinkCache._graph_nodes = {}

        source = _uuid()
        target = _uuid()

        result1: list[dict[str, Any]] = LinkCache.get_constrained(source, target)
        result2: list[dict[str, Any]] = LinkCache.get_constrained(source, target)
        assert result1 is result2

    def test_get_returns_constrained_nodes(self) -> None:
        source = _uuid()
        target = _uuid()
        node_id = _uuid()
        ng_id = _uuid()

        LinkCache._ready = True
        LinkCache._cache = {}
        LinkCache._unconstrained = {}
        LinkCache._graph_nodes = {
            source: [{"node": node_id, "nodegroup": ng_id, "targets": {target}}],
        }

        result: list[dict[str, Any]] = LinkCache.get(source, target)
        assert len(result) == 1
        assert result[0]["node"] == node_id
        assert result[0]["nodegroup"] == ng_id

    def test_get_includes_unconstrained_nodes(self) -> None:
        source = _uuid()
        target = _uuid()
        node_id = _uuid()
        ng_id = _uuid()

        LinkCache._ready = True
        LinkCache._cache = {}
        LinkCache._graph_nodes = {}
        LinkCache._unconstrained = {
            source: [{"node": node_id, "nodegroup": ng_id, "targets": set()}],
        }

        result: list[dict[str, Any]] = LinkCache.get(source, target)
        assert len(result) == 1
        assert result[0]["node"] == node_id

    def test_get_constrained_excludes_unconstrained(self) -> None:
        source = _uuid()
        target = _uuid()
        node_id = _uuid()
        ng_id = _uuid()

        LinkCache._ready = True
        LinkCache._constrained_cache = {}
        LinkCache._graph_nodes = {}
        LinkCache._unconstrained = {
            source: [{"node": node_id, "nodegroup": ng_id, "targets": set()}],
        }

        result: list[dict[str, Any]] = LinkCache.get_constrained(source, target)
        assert result == []

    def test_get_does_not_match_wrong_target(self) -> None:
        source = _uuid()
        target = _uuid()
        wrong_target = _uuid()

        LinkCache._ready = True
        LinkCache._cache = {}
        LinkCache._unconstrained = {}
        LinkCache._graph_nodes = {
            source: [
                {"node": _uuid(), "nodegroup": _uuid(), "targets": {wrong_target}}
            ],
        }

        result: list[dict[str, Any]] = LinkCache.get(source, target)
        assert result == []

    def test_get_triggers_init_if_not_ready(self) -> None:
        LinkCache._ready = False

        with patch.object(LinkCache, "_init") as mock_init:

            def mark_ready() -> None:
                LinkCache._ready = True
                LinkCache._cache = {}
                LinkCache._graph_nodes = {}
                LinkCache._unconstrained = {}

            mock_init.side_effect = mark_ready
            LinkCache.get(_uuid(), _uuid())
            mock_init.assert_called_once()

    def test_get_constrained_triggers_init_if_not_ready(self) -> None:
        LinkCache._ready = False

        with patch.object(LinkCache, "_init") as mock_init:

            def mark_ready() -> None:
                LinkCache._ready = True
                LinkCache._constrained_cache = {}
                LinkCache._graph_nodes = {}

            mock_init.side_effect = mark_ready
            LinkCache.get_constrained(_uuid(), _uuid())
            mock_init.assert_called_once()

    def test_get_combines_constrained_and_unconstrained(self) -> None:
        source = _uuid()
        target = _uuid()
        constrained_node = _uuid()
        unconstrained_node = _uuid()
        ng_a = _uuid()
        ng_b = _uuid()

        LinkCache._ready = True
        LinkCache._cache = {}
        LinkCache._graph_nodes = {
            source: [
                {"node": constrained_node, "nodegroup": ng_a, "targets": {target}}
            ],
        }
        LinkCache._unconstrained = {
            source: [{"node": unconstrained_node, "nodegroup": ng_b, "targets": set()}],
        }

        result: list[dict[str, Any]] = LinkCache.get(source, target)
        assert len(result) == 2
        nodes = {r["node"] for r in result}
        assert constrained_node in nodes
        assert unconstrained_node in nodes

    def test_different_source_target_pairs_cached_separately(self) -> None:
        source_a = _uuid()
        source_b = _uuid()
        target = _uuid()

        node_a = _uuid()
        node_b = _uuid()

        LinkCache._ready = True
        LinkCache._cache = {}
        LinkCache._unconstrained = {}
        LinkCache._graph_nodes = {
            source_a: [{"node": node_a, "nodegroup": _uuid(), "targets": {target}}],
            source_b: [{"node": node_b, "nodegroup": _uuid(), "targets": {target}}],
        }

        result_a: list[dict[str, Any]] = LinkCache.get(source_a, target)
        result_b: list[dict[str, Any]] = LinkCache.get(source_b, target)

        assert len(result_a) == 1
        assert result_a[0]["node"] == node_a
        assert len(result_b) == 1
        assert result_b[0]["node"] == node_b

    def test_multiple_constrained_targets_from_same_source(self) -> None:
        source = _uuid()
        target_a = _uuid()
        target_b = _uuid()

        LinkCache._ready = True
        LinkCache._cache = {}
        LinkCache._unconstrained = {}
        LinkCache._graph_nodes = {
            source: [
                {"node": _uuid(), "nodegroup": _uuid(), "targets": {target_a}},
                {"node": _uuid(), "nodegroup": _uuid(), "targets": {target_b}},
            ],
        }

        result_a: list[dict[str, Any]] = LinkCache.get(source, target_a)
        result_b: list[dict[str, Any]] = LinkCache.get(source, target_b)

        assert len(result_a) == 1
        assert len(result_b) == 1

    def test_node_targeting_multiple_graphs(self) -> None:
        source = _uuid()
        target_a = _uuid()
        target_b = _uuid()
        node = _uuid()
        ng = _uuid()

        LinkCache._ready = True
        LinkCache._cache = {}
        LinkCache._unconstrained = {}
        LinkCache._graph_nodes = {
            source: [{"node": node, "nodegroup": ng, "targets": {target_a, target_b}}],
        }

        result_a: list[dict[str, Any]] = LinkCache.get(source, target_a)
        result_b: list[dict[str, Any]] = LinkCache.get(source, target_b)

        assert len(result_a) == 1
        assert len(result_b) == 1
        assert result_a[0]["node"] == node
        assert result_b[0]["node"] == node


class TestLinkCacheIsChildNodegroup:
    def test_is_child(self) -> None:
        with patch.object(LinkCache, "_init"):
            LinkCache._ready = True
            ng = _uuid()
            LinkCache._child_nodegroups = {ng}

            assert LinkCache.is_child_nodegroup(ng) is True

    def test_is_not_child(self) -> None:
        with patch.object(LinkCache, "_init"):
            LinkCache._ready = True
            LinkCache._child_nodegroups = {_uuid()}

            assert LinkCache.is_child_nodegroup(_uuid()) is False

    def test_empty_set(self) -> None:
        with patch.object(LinkCache, "_init"):
            LinkCache._ready = True
            LinkCache._child_nodegroups = set()

            assert LinkCache.is_child_nodegroup(_uuid()) is False

    def test_triggers_init_if_not_ready(self) -> None:
        LinkCache._ready = False

        with patch.object(LinkCache, "_init") as mock_init:

            def mark_ready() -> None:
                LinkCache._ready = True
                LinkCache._child_nodegroups = set()

            mock_init.side_effect = mark_ready
            LinkCache.is_child_nodegroup(_uuid())
            mock_init.assert_called_once()


class TestLinkCacheClear:
    def test_clears_all_state(self) -> None:
        LinkCache._ready = True
        LinkCache._cache = {("a", "b"): []}
        LinkCache._constrained_cache = {("a", "b"): []}
        LinkCache._graph_nodes = {"a": []}
        LinkCache._unconstrained = {"a": []}
        LinkCache._child_nodegroups = {"ng"}

        LinkCache.clear()

        assert LinkCache._ready is False
        assert LinkCache._cache == {}
        assert LinkCache._constrained_cache == {}
        assert LinkCache._graph_nodes == {}
        assert LinkCache._unconstrained == {}
        assert LinkCache._child_nodegroups == set()

    def test_clear_idempotent(self) -> None:
        LinkCache.clear()
        LinkCache.clear()
        assert LinkCache._ready is False

    def test_clear_invalidates_cached_lookups(self) -> None:
        source = _uuid()
        target = _uuid()

        LinkCache._ready = True
        LinkCache._cache = {(source, target): [{"node": "n1", "nodegroup": "ng1"}]}
        LinkCache._constrained_cache = {}
        LinkCache._graph_nodes = {}
        LinkCache._unconstrained = {}

        cached: list[dict[str, Any]] = LinkCache.get(source, target)
        assert len(cached) == 1

        LinkCache.clear()

        with patch.object(LinkCache, "_init") as mock_init:

            def mark_ready() -> None:
                LinkCache._ready = True
                LinkCache._cache = {}
                LinkCache._graph_nodes = {}
                LinkCache._unconstrained = {}

            mock_init.side_effect = mark_ready

            fresh: list[dict[str, Any]] = LinkCache.get(source, target)
            assert fresh == []
