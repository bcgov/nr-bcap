from __future__ import annotations

from unittest.mock import MagicMock

from typing_extensions import Any

from bcap.search_components.cross_model_advanced_search import CardFilter
from helper import _uuid


class TestCardFilterIsValid:
    def test_none(self) -> None:
        cf = CardFilter()
        assert cf._is_valid(None) is False

    def test_empty_string(self) -> None:
        cf = CardFilter()
        assert cf._is_valid("") is False

    def test_empty_dict(self) -> None:
        cf = CardFilter()
        assert cf._is_valid({}) is False

    def test_null_op(self) -> None:
        cf = CardFilter()
        assert cf._is_valid({"op": "null"}) is True

    def test_not_null_op(self) -> None:
        cf = CardFilter()
        assert cf._is_valid({"op": "not_null"}) is True

    def test_val_null_string(self) -> None:
        cf = CardFilter()
        assert cf._is_valid({"op": "eq", "val": "null"}) is True

    def test_val_not_null_string(self) -> None:
        cf = CardFilter()
        assert cf._is_valid({"op": "eq", "val": "not_null"}) is True

    def test_val_zero_integer(self) -> None:
        cf = CardFilter()
        assert cf._is_valid({"op": "eq", "val": 0}) is True

    def test_val_false_boolean(self) -> None:
        cf = CardFilter()
        assert cf._is_valid({"op": "eq", "val": False}) is True

    def test_val_empty_string(self) -> None:
        cf = CardFilter()
        assert cf._is_valid({"op": "eq", "val": ""}) is False

    def test_val_none(self) -> None:
        cf = CardFilter()
        assert cf._is_valid({"op": "eq", "val": None}) is False

    def test_val_whitespace_string(self) -> None:
        cf = CardFilter()
        assert cf._is_valid({"op": "eq", "val": " "}) is True

    def test_val_empty_list(self) -> None:
        cf = CardFilter()
        assert cf._is_valid({"op": "eq", "val": []}) is False

    def test_val_nonempty_list(self) -> None:
        cf = CardFilter()
        assert cf._is_valid({"op": "eq", "val": [{"resourceId": "abc"}]}) is True

    def test_plain_string_truthy(self) -> None:
        cf = CardFilter()
        assert cf._is_valid("some-value") is True

    def test_plain_integer(self) -> None:
        cf = CardFilter()
        assert cf._is_valid(42) is True

    def test_plain_zero(self) -> None:
        cf = CardFilter()
        assert cf._is_valid(0) is False

    def test_plain_false(self) -> None:
        cf = CardFilter()
        assert cf._is_valid(False) is False

    def test_dict_with_op_only_no_val_key(self) -> None:
        cf = CardFilter()
        assert cf._is_valid({"op": "eq"}) is False

    def test_dict_with_op_null_and_extra_keys(self) -> None:
        cf = CardFilter()
        assert cf._is_valid({"op": "null", "extra": "ignored"}) is True

    def test_nested_dict_val_is_dict(self) -> None:
        cf = CardFilter()
        assert cf._is_valid({"op": "eq", "val": {"nested": "thing"}}) is True


class TestCardFilterBuildResourceInstanceQuery:
    def test_val_is_none(self) -> None:
        cf = CardFilter()
        result = cf._build_resource_instance_query("node-1", {"val": None})
        assert result is None

    def test_single_resource_id(self) -> None:
        cf = CardFilter()
        result = cf._build_resource_instance_query(
            "node-1",
            {"val": [{"resourceId": "abc-123"}]},
        )
        assert result is not None

    def test_multiple_resource_ids(self) -> None:
        cf = CardFilter()
        result = cf._build_resource_instance_query(
            "node-1",
            {"val": [{"resourceId": "abc-123"}, {"resourceId": "def-456"}]},
        )
        assert result is not None

    def test_mixed_dicts_some_without_resource_id(self) -> None:
        cf = CardFilter()
        result = cf._build_resource_instance_query(
            "node-1",
            {"val": [{"resourceId": "abc"}, {"other": "val"}]},
        )
        assert result is not None

    def test_no_resource_ids_in_dicts(self) -> None:
        cf = CardFilter()
        result = cf._build_resource_instance_query(
            "node-1",
            {"val": [{"notResourceId": "abc"}]},
        )
        assert result is None

    def test_single_dict_not_list(self) -> None:
        cf = CardFilter()
        result = cf._build_resource_instance_query(
            "node-1",
            {"val": {"resourceId": "abc-123"}},
        )
        assert result is not None

    def test_empty_list_val(self) -> None:
        cf = CardFilter()
        result = cf._build_resource_instance_query(
            "node-1",
            {"val": []},
        )
        assert result is None

    def test_multiple_resource_ids_produces_should_clauses(self) -> None:
        cf = CardFilter()
        result = cf._build_resource_instance_query(
            "node-1",
            {"val": [
                {"resourceId": "abc-123"},
                {"resourceId": "def-456"},
                {"resourceId": "ghi-789"},
            ]},
        )
        assert result is not None
        assert len(result.dsl["bool"]["should"]) == 3

    def test_dict_val_without_resource_id(self) -> None:
        cf = CardFilter()
        result = cf._build_resource_instance_query(
            "node-1",
            {"val": {"notResourceId": "abc"}},
        )
        assert result is None


class TestCardFilterBuild:
    def test_empty_filters(self) -> None:
        cf = CardFilter(filters={})
        factory = MagicMock()
        nodes: dict[str, Any] = {}
        request = MagicMock()
        query, _negation_query, _null_query = cf.build(factory, nodes, request)
        assert query.dsl["bool"]["must"] == []

    def test_skips_invalid_filter(self) -> None:
        node_id = _uuid()
        node = MagicMock()
        node.datatype = "string"
        node.nodeid = node_id
        cf = CardFilter(filters={node_id: {"op": "eq", "val": ""}})
        factory = MagicMock()
        nodes: dict[str, Any] = {node_id: node}
        request = MagicMock()
        query, _negation_query, _null_query = cf.build(factory, nodes, request)
        assert query.dsl["bool"]["must"] == []

    def test_skips_unknown_node(self) -> None:
        node_id = _uuid()
        cf = CardFilter(filters={node_id: {"op": "eq", "val": "test"}})
        factory = MagicMock()
        nodes: dict[str, Any] = {}
        request = MagicMock()
        query, _negation_query, _null_query = cf.build(factory, nodes, request)
        assert query.dsl["bool"]["must"] == []

    def test_all_filters_invalid_produces_empty_query(self) -> None:
        node_a = _uuid()
        node_b = _uuid()
        cf = CardFilter(filters={
            node_a: {"op": "eq", "val": ""},
            node_b: {"op": "eq", "val": None},
        })
        factory = MagicMock()
        nodes: dict[str, Any] = {}
        request = MagicMock()
        query, _negation_query, _null_query = cf.build(factory, nodes, request)
        assert query.dsl["bool"]["must"] == []

    def test_mix_of_valid_and_unknown_nodes(self) -> None:
        known_id = _uuid()
        unknown_id = _uuid()
        node = MagicMock()
        node.datatype = "string"
        node.nodeid = known_id
        cf = CardFilter(filters={
            known_id: {"op": "null"},
            unknown_id: {"op": "eq", "val": "test"},
        })
        factory = MagicMock()
        nodes: dict[str, Any] = {known_id: node}
        request = MagicMock()
        _query, _negation_query, _null_query = cf.build(factory, nodes, request)


class TestCardFilterCreate:
    def test_empty(self) -> None:
        cf = CardFilter.create({})
        assert cf.filters == {}
        assert cf.nodegroup is None

    def test_with_data(self) -> None:
        ng = _uuid()
        node_id = _uuid()
        cf = CardFilter.create({
            "filters": {node_id: {"op": "eq", "val": "test"}},
            "nodegroup_id": ng,
        })
        assert cf.nodegroup == ng
        assert node_id in cf.filters

    def test_missing_filters_key(self) -> None:
        cf = CardFilter.create({"nodegroup_id": "ng-1"})
        assert cf.filters == {}
        assert cf.nodegroup == "ng-1"

    def test_missing_nodegroup_key(self) -> None:
        cf = CardFilter.create({"filters": {"n": {"op": "eq"}}})
        assert cf.nodegroup is None
        assert "n" in cf.filters

    def test_none_filters_value(self) -> None:
        cf = CardFilter.create({"filters": None})
        assert cf.filters is None or cf.filters == {}

    def test_none_nodegroup_value(self) -> None:
        cf = CardFilter.create({"nodegroup_id": None})
        assert cf.nodegroup is None

    def test_filters_with_many_nodes(self) -> None:
        node_ids = [_uuid() for _ in range(20)]
        filters = {nid: {"op": "eq", "val": f"val-{i}"} for i, nid in enumerate(node_ids)}
        cf = CardFilter.create({"filters": filters})
        assert len(cf.filters) == 20

    def test_extra_keys_ignored(self) -> None:
        cf = CardFilter.create({
            "filters": {},
            "nodegroup_id": "ng-1",
            "unknown_key": "should-be-ignored",
            "another": 42,
        })
        assert cf.nodegroup == "ng-1"
        assert cf.filters == {}
