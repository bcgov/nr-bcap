from __future__ import annotations

import pytest
from typing_extensions import Any

from bcap.search_components.cross_model_advanced_search import Linker

C1 = "http://example.com/concept/1"
C2 = "http://example.com/concept/2"


def _uris(*paths: str) -> list[dict[str, str]]:
    return [{"uri": p} for p in paths]


def _p(tile_value: Any, filter_val: Any, op: str, expected: bool, id: str):
    return pytest.param(tile_value, filter_val, op, expected, id=id)


class TestLinkerValueMatches:
    @pytest.mark.parametrize(
        "tile_value,filter_val,op,expected",
        [
            _p(None, "test", "eq", False, "none_tile_value"),
            _p("abc", "abc", "eq", True, "eq_match"),
            _p("abc", "xyz", "eq", False, "eq_no_match"),
            _p("abc", "xyz", "neq", True, "neq_match"),
            _p("abc", "abc", "neq", False, "neq_no_match"),
            _p("abc", "xyz", "!eq", True, "not_eq_alias_match"),
            _p("abc", "abc", "!eq", False, "not_eq_alias_no_match"),
            _p("abc", "abc", "unknown", False, "unknown_op"),
            _p("abc", None, "eq", False, "eq_none_filter_val"),
            _p("abc", None, "neq", True, "neq_none_filter_val"),
            _p("", "", "eq", True, "eq_empty_string_vs_empty_string"),
            _p(10, 5, "gt", True, "gt_greater"),
            _p(5, 10, "gt", False, "gt_lesser"),
            _p(5, 5, "gt", False, "gt_equal"),
            _p(10, 5, "gte", True, "gte_greater"),
            _p(5, 5, "gte", True, "gte_equal"),
            _p(4, 5, "gte", False, "gte_lesser"),
            _p(3, 5, "lt", True, "lt_lesser"),
            _p(5, 5, "lt", False, "lt_equal"),
            _p(10, 5, "lt", False, "lt_greater"),
            _p(3, 5, "lte", True, "lte_lesser"),
            _p(5, 5, "lte", True, "lte_equal"),
            _p(10, 5, "lte", False, "lte_greater"),
            _p(42, 42, "eq", True, "eq_numeric_match"),
            _p(42, 43, "eq", False, "eq_numeric_no_match"),
            _p(42, "42", "eq", False, "eq_type_mismatch_int_vs_string"),
            _p("b", "a", "gt", True, "gt_string_comparison"),
            _p("a", "b", "gt", False, "gt_string_comparison_no_match"),
            _p(-1, -5, "gt", True, "gt_negative_numbers"),
            _p(-5, -1, "gt", False, "gt_negative_numbers_no_match"),
            _p(0.1 + 0.2, 0.3, "gt", True, "gt_float_precision"),
            _p(0.3, 0.1 + 0.2, "lt", True, "lt_float_precision"),
            _p(5.0, 5, "lte", True, "lte_boundary_float"),
            _p(5, 5.0, "gte", True, "gte_boundary_float"),
            _p(True, True, "eq", True, "eq_boolean_match"),
            _p(True, False, "eq", False, "eq_boolean_no_match"),
            _p(_uris(C1), _uris(C1), "eq", True, "concept_uri_eq_match"),
            _p(_uris(C1), _uris(C2), "eq", False, "concept_uri_eq_no_match"),
            _p(_uris(C1), _uris(C2), "neq", True, "concept_uri_neq"),
            _p(_uris(C1), _uris(C1), "neq", False, "concept_uri_neq_same_uri"),
            _p(_uris(C1), _uris(C2), "!eq", True, "concept_uri_not_eq_alias"),
            _p({"uri": C1}, _uris(C1), "eq", True, "concept_uri_tile_dict_not_list"),
            _p(
                _uris(C1, C2),
                _uris(C2),
                "eq",
                True,
                "concept_uri_multiple_uris_overlap",
            ),
            _p(
                _uris(C1), _uris(C1, C2), "eq", True, "concept_uri_multiple_filter_uris"
            ),
            _p([], _uris(C1), "eq", False, "concept_uri_empty_tile_list"),
            _p(_uris(C1), [], "eq", False, "concept_uri_empty_filter_list"),
            _p(
                [{"someKey": "val"}],
                _uris(C1),
                "eq",
                False,
                "concept_uri_no_matching_uris",
            ),
            _p(
                [{"id": "1"}],
                [{"id": "1"}],
                "eq",
                False,
                "concept_uri_both_have_no_uri_key",
            ),
            _p(
                _uris(C1),
                ["not-a-dict", {"uri": C1}],
                "eq",
                True,
                "concept_uri_filter_list_has_non_dict_items",
            ),
            _p(
                ["not-a-dict", {"uri": C1}],
                _uris(C1),
                "eq",
                True,
                "concept_uri_tile_list_has_non_dict_items",
            ),
            _p(
                _uris(C1, C2),
                _uris("http://b.com/1", "http://b.com/2"),
                "neq",
                True,
                "concept_uri_neq_no_overlap_at_all",
            ),
            _p(
                _uris(C1, C2),
                _uris(C1, C2),
                "neq",
                False,
                "concept_uri_neq_full_overlap",
            ),
        ],
    )
    def test_value_matches(
        self, tile_value: Any, filter_val: Any, op: str, expected: bool
    ) -> None:
        assert Linker()._value_matches(tile_value, filter_val, op) is expected


class TestLinkerTileMatchesFilters:
    @pytest.mark.parametrize(
        "data,filters,expected",
        [
            pytest.param({"a": 1}, {}, True, id="empty_filters"),
            pytest.param({}, {}, True, id="empty_data_empty_filters"),
            pytest.param(
                {}, {"node-1": {"op": "eq", "val": "abc"}}, False, id="empty_data"
            ),
            pytest.param(
                {"node-1": "abc"},
                {"node-1": {"op": "eq", "val": "abc"}},
                True,
                id="matching_filters",
            ),
            pytest.param(
                {"node-1": "abc"},
                {"node-1": {"op": "eq", "val": "xyz"}},
                False,
                id="non_matching_filters",
            ),
            pytest.param(
                {"other-node": "abc"},
                {"node-1": {"op": "eq", "val": "abc"}},
                False,
                id="missing_node_in_data",
            ),
            pytest.param(
                {"node-1": None},
                {"node-1": {"op": "eq", "val": "abc"}},
                False,
                id="none_value_in_data",
            ),
            pytest.param(
                {"node-1": "abc"},
                {"node-1": {"val": "abc"}},
                True,
                id="default_op_is_eq",
            ),
            pytest.param(
                {"node-1": "abc"},
                {"node-1": {"op": "regex", "val": "abc"}},
                False,
                id="filter_with_unknown_op",
            ),
            pytest.param(
                {"node-1": "abc", "node-2": 10},
                {
                    "node-1": {"op": "eq", "val": "abc"},
                    "node-2": {"op": "gt", "val": 5},
                },
                True,
                id="multiple_filters_all_match",
            ),
            pytest.param(
                {"node-1": "abc", "node-2": 3},
                {
                    "node-1": {"op": "eq", "val": "abc"},
                    "node-2": {"op": "gt", "val": 5},
                },
                False,
                id="multiple_filters_one_fails",
            ),
            pytest.param(
                {"node-1": "wrong", "node-2": "correct"},
                {
                    "node-1": {"op": "eq", "val": "expected"},
                    "node-2": {"op": "eq", "val": "correct"},
                },
                False,
                id="first_filter_fails_short_circuits",
            ),
            pytest.param(
                {"node-1": "abc", "node-2": "xyz", "node-3": 99},
                {"node-1": {"op": "eq", "val": "abc"}},
                True,
                id="data_has_extra_keys_beyond_filters",
            ),
            pytest.param(
                {"node-1": _uris(C1)},
                {"node-1": {"op": "eq", "val": _uris(C1)}},
                True,
                id="concept_uri_filter_in_tile",
            ),
            pytest.param(
                {"node-1": _uris(C1)},
                {"node-1": {"op": "eq", "val": _uris(C2)}},
                False,
                id="concept_uri_filter_mismatch_in_tile",
            ),
            pytest.param(
                {"node-1": _uris(C1), "node-2": 42},
                {
                    "node-1": {"op": "eq", "val": _uris(C1)},
                    "node-2": {"op": "gte", "val": 40},
                },
                True,
                id="mixed_concept_and_scalar_filters",
            ),
        ],
    )
    def test_tile_matches_filters(
        self, data: dict[str, Any], filters: dict[str, Any], expected: bool
    ) -> None:
        assert Linker()._tile_matches_filters(data, filters) is expected
