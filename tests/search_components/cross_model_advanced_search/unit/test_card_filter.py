from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from typing_extensions import Any

from bcap.search_components.cross_model_advanced_search import CardFilter
from helper import _uuid


def _string_node(node_id: str) -> MagicMock:
    node = MagicMock()
    node.datatype = "string"
    node.nodeid = node_id
    return node


class TestCardFilterIsValid:
    @pytest.mark.parametrize(
        "value,expected",
        [
            pytest.param(None, False, id="none"),
            pytest.param("", False, id="empty_string"),
            pytest.param({}, False, id="empty_dict"),
            pytest.param({"op": "null"}, True, id="null_op"),
            pytest.param({"op": "not_null"}, True, id="not_null_op"),
            pytest.param(
                {"op": "null", "extra": "ignored"},
                True,
                id="dict_with_op_null_and_extra_keys",
            ),
            pytest.param({"op": "eq"}, False, id="dict_with_op_only_no_val_key"),
            pytest.param({"op": "eq", "val": "null"}, True, id="val_null_string"),
            pytest.param(
                {"op": "eq", "val": "not_null"}, True, id="val_not_null_string"
            ),
            pytest.param({"op": "eq", "val": 0}, True, id="val_zero_integer"),
            pytest.param({"op": "eq", "val": False}, True, id="val_false_boolean"),
            pytest.param({"op": "eq", "val": ""}, False, id="val_empty_string"),
            pytest.param({"op": "eq", "val": None}, False, id="val_none"),
            pytest.param({"op": "eq", "val": " "}, True, id="val_whitespace_string"),
            pytest.param({"op": "eq", "val": []}, False, id="val_empty_list"),
            pytest.param(
                {"op": "eq", "val": [{"resourceId": "abc"}]},
                True,
                id="val_nonempty_list",
            ),
            pytest.param(
                {"op": "eq", "val": {"nested": "thing"}},
                True,
                id="nested_dict_val_is_dict",
            ),
            pytest.param("some-value", True, id="plain_string_truthy"),
            pytest.param(42, True, id="plain_integer"),
            pytest.param(0, False, id="plain_zero"),
            pytest.param(False, False, id="plain_false"),
        ],
    )
    def test_is_valid(self, value: Any, expected: bool) -> None:
        assert CardFilter()._is_valid(value) is expected


class TestCardFilterBuildResourceInstanceQuery:
    @pytest.mark.parametrize(
        "val,builds",
        [
            pytest.param(None, False, id="val_is_none"),
            pytest.param([], False, id="empty_list_val"),
            pytest.param([{"resourceId": "abc-123"}], True, id="single_resource_id"),
            pytest.param(
                [{"resourceId": "abc-123"}, {"resourceId": "def-456"}],
                True,
                id="multiple_resource_ids",
            ),
            pytest.param(
                [{"resourceId": "abc"}, {"other": "val"}],
                True,
                id="mixed_dicts_some_without_resource_id",
            ),
            pytest.param(
                [{"notResourceId": "abc"}], False, id="no_resource_ids_in_dicts"
            ),
            pytest.param({"resourceId": "abc-123"}, True, id="single_dict_not_list"),
            pytest.param(
                {"notResourceId": "abc"}, False, id="dict_val_without_resource_id"
            ),
        ],
    )
    def test_builds_only_when_a_resource_id_is_present(
        self, val: Any, builds: bool
    ) -> None:
        result = CardFilter()._build_resource_instance_query("node-1", {"val": val})
        assert (result is not None) is builds

    def test_one_should_clause_per_resource_id(self) -> None:
        result = CardFilter()._build_resource_instance_query(
            "node-1",
            {"val": [{"resourceId": r} for r in ("abc-123", "def-456", "ghi-789")]},
        )
        assert result is not None
        assert len(result.dsl["bool"]["should"]) == 3


class TestCardFilterBuild:
    def test_empty_filters(self) -> None:
        query, _negation, _null = CardFilter(filters={}).build(
            MagicMock(), {}, MagicMock()
        )
        assert query.dsl["bool"]["must"] == []

    @pytest.mark.parametrize(
        "known",
        [
            pytest.param(False, id="skips_unknown_node"),
            pytest.param(True, id="skips_invalid_filter"),
        ],
    )
    def test_skips_filters_that_produce_nothing(self, known: bool) -> None:
        node_id = _uuid()
        cf = CardFilter(
            filters={
                node_id: {"op": "eq", "val": "" if known else "test"},
                _uuid(): {"op": "eq", "val": None},
            }
        )
        nodes: dict[str, Any] = {node_id: _string_node(node_id)} if known else {}
        query, _negation, _null = cf.build(MagicMock(), nodes, MagicMock())
        assert query.dsl["bool"]["must"] == []


class TestCardFilterCreate:
    @pytest.mark.parametrize(
        "data,filters,nodegroup",
        [
            pytest.param({}, {}, None, id="empty"),
            pytest.param(
                {"nodegroup_id": "ng-1"}, {}, "ng-1", id="missing_filters_key"
            ),
            pytest.param(
                {"filters": {"n": {"op": "eq"}}},
                {"n": {"op": "eq"}},
                None,
                id="missing_nodegroup_key",
            ),
            pytest.param(
                {"filters": None, "nodegroup_id": None},
                None,
                None,
                id="none_filters_and_nodegroup",
            ),
            pytest.param(
                {
                    "filters": {},
                    "nodegroup_id": "ng-1",
                    "unknown_key": "x",
                    "another": 42,
                },
                {},
                "ng-1",
                id="extra_keys_ignored",
            ),
        ],
    )
    def test_create(self, data: dict[str, Any], filters: Any, nodegroup: Any) -> None:
        cf = CardFilter.create(data)
        assert cf.filters == filters
        assert cf.nodegroup == nodegroup

    def test_carries_the_payload_through(self) -> None:
        ng, node_id = _uuid(), _uuid()
        cf = CardFilter.create(
            {"filters": {node_id: {"op": "eq", "val": "test"}}, "nodegroup_id": ng}
        )
        assert cf.nodegroup == ng
        assert node_id in cf.filters
