from __future__ import annotations

from unittest.mock import MagicMock, patch

from typing_extensions import Any

from bcap.search_components.cross_model_advanced_search import CardFilter
from helper import _make_bool, _make_node, _uuid


class TestCardFilterBuild:
    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_resource_instance_node_delegates(self, mock_bool_cls: MagicMock) -> None:
        mock_bool_cls.return_value = _make_bool()
        node_id = _uuid()
        node = _make_node(datatype="resource-instance", node_id=node_id)
        cf = CardFilter(filters={node_id: {"val": [{"resourceId": "abc"}]}})
        factory = MagicMock()
        nodes: dict[str, Any] = {node_id: node}
        request = MagicMock()
        cf.build(factory, nodes, request)
        factory.get_instance.assert_not_called()

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_resource_instance_list_node_delegates(
        self, mock_bool_cls: MagicMock
    ) -> None:
        mock_bool_cls.return_value = _make_bool()
        node_id = _uuid()
        node = _make_node(datatype="resource-instance-list", node_id=node_id)
        cf = CardFilter(filters={node_id: {"val": [{"resourceId": "abc"}]}})
        factory = MagicMock()
        nodes: dict[str, Any] = {node_id: node}
        request = MagicMock()
        cf.build(factory, nodes, request)
        factory.get_instance.assert_not_called()

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_resource_instance_null_op_uses_standard_path(
        self, mock_bool_cls: MagicMock
    ) -> None:
        mock_bool_cls.return_value = _make_bool()
        node_id = _uuid()
        node = _make_node(datatype="resource-instance", node_id=node_id)
        cf = CardFilter(filters={node_id: {"op": "null", "val": "null"}})
        factory = MagicMock()
        mock_dt = MagicMock()
        factory.get_instance.return_value = mock_dt
        nodes: dict[str, Any] = {node_id: node}
        request = MagicMock()
        cf.build(factory, nodes, request)
        factory.get_instance.assert_called_once_with("resource-instance")

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_standard_datatype_delegates_to_factory(
        self, mock_bool_cls: MagicMock
    ) -> None:
        mock_bool_cls.return_value = _make_bool()
        node_id = _uuid()
        node = _make_node(datatype="string", node_id=node_id)
        cf = CardFilter(filters={node_id: {"op": "eq", "val": "test"}})
        factory = MagicMock()
        mock_dt = MagicMock()
        factory.get_instance.return_value = mock_dt
        nodes: dict[str, Any] = {node_id: node}
        request = MagicMock()
        cf.build(factory, nodes, request)
        factory.get_instance.assert_called_once_with("string")
        mock_dt.append_search_filters.assert_called_once()

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_null_op_routes_to_null_query(self, mock_bool_cls: MagicMock) -> None:
        mock_query = _make_bool()
        mock_null_query = _make_bool()
        mock_negation_query = _make_bool()
        mock_bool_cls.side_effect = [mock_negation_query, mock_null_query, mock_query]
        node_id = _uuid()
        node = _make_node(datatype="string", node_id=node_id)
        cf = CardFilter(filters={node_id: {"op": "null", "val": "null"}})
        factory = MagicMock()
        mock_dt = MagicMock()
        factory.get_instance.return_value = mock_dt
        nodes: dict[str, Any] = {node_id: node}
        request = MagicMock()
        _query, _negation_query, null_query = cf.build(factory, nodes, request)
        mock_dt.append_search_filters.assert_called_once()
        call_args = mock_dt.append_search_filters.call_args
        assert call_args[0][2] is null_query

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_multiple_nodes_all_processed(self, mock_bool_cls: MagicMock) -> None:
        mock_bool_cls.return_value = _make_bool()
        node_a = _uuid()
        node_b = _uuid()
        na = _make_node(datatype="string", node_id=node_a)
        nb = _make_node(datatype="number", node_id=node_b)
        cf = CardFilter(
            filters={
                node_a: {"op": "eq", "val": "test"},
                node_b: {"op": "gt", "val": 5},
            }
        )
        factory = MagicMock()
        mock_dt = MagicMock()
        factory.get_instance.return_value = mock_dt
        nodes: dict[str, Any] = {node_a: na, node_b: nb}
        request = MagicMock()
        cf.build(factory, nodes, request)
        assert mock_dt.append_search_filters.call_count == 2

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_datatype_without_append_search_filters(
        self, mock_bool_cls: MagicMock
    ) -> None:
        mock_bool_cls.return_value = _make_bool()
        node_id = _uuid()
        node = _make_node(datatype="string", node_id=node_id)
        cf = CardFilter(filters={node_id: {"op": "eq", "val": "test"}})
        factory = MagicMock()
        mock_dt = MagicMock(spec=[])
        factory.get_instance.return_value = mock_dt
        nodes: dict[str, Any] = {node_id: node}
        request = MagicMock()
        _query, _negation_query, _null_query = cf.build(factory, nodes, request)
