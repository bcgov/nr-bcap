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
            (None, False),
            ("", False),
            ({}, False),
            ({"op": "null"}, True),
            ({"op": "not_null"}, True),
            ({"op": "null", "extra": "ignored"}, True),
            ({"op": "eq"}, False),
            ({"op": "eq", "val": "null"}, True),
            ({"op": "eq", "val": "not_null"}, True),
            ({"op": "eq", "val": 0}, True),
            ({"op": "eq", "val": False}, True),
            ({"op": "eq", "val": ""}, False),
            ({"op": "eq", "val": None}, False),
            ({"op": "eq", "val": " "}, True),
            ({"op": "eq", "val": []}, False),
            ({"op": "eq", "val": [{"resourceId": "abc"}]}, True),
            ({"op": "eq", "val": {"nested": "thing"}}, True),
            ("some-value", True),
            (42, True),
            (0, False),
            (False, False),
        ],
    )
    def test_is_valid(self, value: Any, expected: bool) -> None:
        assert CardFilter()._is_valid(value) is expected


class TestCardFilterBuildResourceInstanceQuery:
    @pytest.mark.parametrize(
        "val,builds",
        [
            (None, False),
            ([], False),
            ([{"resourceId": "abc-123"}], True),
            ([{"resourceId": "abc-123"}, {"resourceId": "def-456"}], True),
            ([{"resourceId": "abc"}, {"other": "val"}], True),
            ([{"notResourceId": "abc"}], False),
            ({"resourceId": "abc-123"}, True),
            ({"notResourceId": "abc"}, False),
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
            pytest.param(False, id="unknown-node"),
            pytest.param(True, id="known-node-invalid-value"),
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
            ({}, {}, None),
            ({"nodegroup_id": "ng-1"}, {}, "ng-1"),
            ({"filters": {"n": {"op": "eq"}}}, {"n": {"op": "eq"}}, None),
            ({"filters": None, "nodegroup_id": None}, None, None),
            (
                {
                    "filters": {},
                    "nodegroup_id": "ng-1",
                    "unknown_key": "x",
                    "another": 42,
                },
                {},
                "ng-1",
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
