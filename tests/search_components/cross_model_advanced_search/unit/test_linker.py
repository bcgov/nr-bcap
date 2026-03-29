from __future__ import annotations

from typing_extensions import Any

from bcap.search_components.cross_model_advanced_search import Linker


class TestLinkerValueMatches:
    def setup_method(self) -> None:
        self.linker = Linker()

    def test_none_tile_value(self) -> None:
        assert self.linker._value_matches(None, "test", "eq") is False

    def test_eq_match(self) -> None:
        assert self.linker._value_matches("abc", "abc", "eq") is True

    def test_eq_no_match(self) -> None:
        assert self.linker._value_matches("abc", "xyz", "eq") is False

    def test_neq_match(self) -> None:
        assert self.linker._value_matches("abc", "xyz", "neq") is True

    def test_neq_no_match(self) -> None:
        assert self.linker._value_matches("abc", "abc", "neq") is False

    def test_not_eq_alias(self) -> None:
        assert self.linker._value_matches("abc", "xyz", "!eq") is True
        assert self.linker._value_matches("abc", "abc", "!eq") is False

    def test_gt(self) -> None:
        assert self.linker._value_matches(10, 5, "gt") is True
        assert self.linker._value_matches(5, 10, "gt") is False
        assert self.linker._value_matches(5, 5, "gt") is False

    def test_gte(self) -> None:
        assert self.linker._value_matches(10, 5, "gte") is True
        assert self.linker._value_matches(5, 5, "gte") is True
        assert self.linker._value_matches(4, 5, "gte") is False

    def test_lt(self) -> None:
        assert self.linker._value_matches(3, 5, "lt") is True
        assert self.linker._value_matches(5, 5, "lt") is False
        assert self.linker._value_matches(10, 5, "lt") is False

    def test_lte(self) -> None:
        assert self.linker._value_matches(3, 5, "lte") is True
        assert self.linker._value_matches(5, 5, "lte") is True
        assert self.linker._value_matches(10, 5, "lte") is False

    def test_unknown_op(self) -> None:
        assert self.linker._value_matches("abc", "abc", "unknown") is False

    def test_concept_uri_eq_match(self) -> None:
        tile_value = [{"uri": "http://example.com/concept/1"}]
        filter_val = [{"uri": "http://example.com/concept/1"}]
        assert self.linker._value_matches(tile_value, filter_val, "eq") is True

    def test_concept_uri_eq_no_match(self) -> None:
        tile_value = [{"uri": "http://example.com/concept/1"}]
        filter_val = [{"uri": "http://example.com/concept/2"}]
        assert self.linker._value_matches(tile_value, filter_val, "eq") is False

    def test_concept_uri_neq(self) -> None:
        tile_value = [{"uri": "http://example.com/concept/1"}]
        filter_val = [{"uri": "http://example.com/concept/2"}]
        assert self.linker._value_matches(tile_value, filter_val, "neq") is True

    def test_concept_uri_tile_dict_not_list(self) -> None:
        tile_value = {"uri": "http://example.com/concept/1"}
        filter_val = [{"uri": "http://example.com/concept/1"}]
        assert self.linker._value_matches(tile_value, filter_val, "eq") is True

    def test_concept_uri_no_matching_uris(self) -> None:
        tile_value = [{"someKey": "val"}]
        filter_val = [{"uri": "http://example.com/concept/1"}]
        assert self.linker._value_matches(tile_value, filter_val, "eq") is False

    def test_concept_uri_neq_same_uri(self) -> None:
        tile_value = [{"uri": "http://example.com/concept/1"}]
        filter_val = [{"uri": "http://example.com/concept/1"}]
        assert self.linker._value_matches(tile_value, filter_val, "neq") is False

    def test_concept_uri_not_eq_alias(self) -> None:
        tile_value = [{"uri": "http://example.com/concept/1"}]
        filter_val = [{"uri": "http://example.com/concept/2"}]
        assert self.linker._value_matches(tile_value, filter_val, "!eq") is True

    def test_concept_uri_multiple_uris_overlap(self) -> None:
        tile_value = [
            {"uri": "http://example.com/concept/1"},
            {"uri": "http://example.com/concept/2"},
        ]
        filter_val = [{"uri": "http://example.com/concept/2"}]
        assert self.linker._value_matches(tile_value, filter_val, "eq") is True

    def test_concept_uri_multiple_filter_uris(self) -> None:
        tile_value = [{"uri": "http://example.com/concept/1"}]
        filter_val = [
            {"uri": "http://example.com/concept/1"},
            {"uri": "http://example.com/concept/2"},
        ]
        assert self.linker._value_matches(tile_value, filter_val, "eq") is True

    def test_concept_uri_empty_tile_list(self) -> None:
        tile_value: list[dict[str, str]] = []
        filter_val = [{"uri": "http://example.com/concept/1"}]
        assert self.linker._value_matches(tile_value, filter_val, "eq") is False

    def test_concept_uri_empty_filter_list(self) -> None:
        tile_value = [{"uri": "http://example.com/concept/1"}]
        filter_val: list[dict[str, str]] = []
        assert self.linker._value_matches(tile_value, filter_val, "eq") is False

    def test_eq_numeric(self) -> None:
        assert self.linker._value_matches(42, 42, "eq") is True
        assert self.linker._value_matches(42, 43, "eq") is False

    def test_gt_string_comparison(self) -> None:
        assert self.linker._value_matches("b", "a", "gt") is True
        assert self.linker._value_matches("a", "b", "gt") is False

    def test_eq_type_mismatch_int_vs_string(self) -> None:
        assert self.linker._value_matches(42, "42", "eq") is False

    def test_gt_float_precision(self) -> None:
        assert self.linker._value_matches(0.1 + 0.2, 0.3, "gt") is True
        assert self.linker._value_matches(0.3, 0.1 + 0.2, "lt") is True

    def test_lte_boundary_float(self) -> None:
        assert self.linker._value_matches(5.0, 5, "lte") is True
        assert self.linker._value_matches(5, 5.0, "gte") is True

    def test_concept_uri_filter_list_has_non_dict_items(self) -> None:
        tile_value = [{"uri": "http://example.com/1"}]
        filter_val = ["not-a-dict", {"uri": "http://example.com/1"}]
        assert self.linker._value_matches(tile_value, filter_val, "eq") is True

    def test_concept_uri_tile_list_has_non_dict_items(self) -> None:
        tile_value = ["not-a-dict", {"uri": "http://example.com/1"}]
        filter_val = [{"uri": "http://example.com/1"}]
        assert self.linker._value_matches(tile_value, filter_val, "eq") is True

    def test_concept_uri_both_have_no_uri_key(self) -> None:
        tile_value = [{"id": "1"}]
        filter_val = [{"id": "1"}]
        assert self.linker._value_matches(tile_value, filter_val, "eq") is False

    def test_neq_none_filter_val(self) -> None:
        assert self.linker._value_matches("abc", None, "neq") is True

    def test_eq_none_filter_val(self) -> None:
        assert self.linker._value_matches("abc", None, "eq") is False

    def test_gt_negative_numbers(self) -> None:
        assert self.linker._value_matches(-1, -5, "gt") is True
        assert self.linker._value_matches(-5, -1, "gt") is False

    def test_eq_boolean_values(self) -> None:
        assert self.linker._value_matches(True, True, "eq") is True
        assert self.linker._value_matches(True, False, "eq") is False

    def test_eq_empty_string_vs_empty_string(self) -> None:
        assert self.linker._value_matches("", "", "eq") is True

    def test_concept_uri_neq_no_overlap_at_all(self) -> None:
        tile_value = [{"uri": "http://a.com/1"}, {"uri": "http://a.com/2"}]
        filter_val = [{"uri": "http://b.com/1"}, {"uri": "http://b.com/2"}]
        assert self.linker._value_matches(tile_value, filter_val, "neq") is True

    def test_concept_uri_neq_full_overlap(self) -> None:
        tile_value = [{"uri": "http://a.com/1"}, {"uri": "http://a.com/2"}]
        filter_val = [{"uri": "http://a.com/1"}, {"uri": "http://a.com/2"}]
        assert self.linker._value_matches(tile_value, filter_val, "neq") is False


class TestLinkerTileMatchesFilters:
    def setup_method(self) -> None:
        self.linker = Linker()

    def test_empty_filters(self) -> None:
        assert self.linker._tile_matches_filters({"a": 1}, {}) is True

    def test_matching_filters(self) -> None:
        data: dict[str, Any] = {"node-1": "abc"}
        filters: dict[str, Any] = {"node-1": {"op": "eq", "val": "abc"}}
        assert self.linker._tile_matches_filters(data, filters) is True

    def test_non_matching_filters(self) -> None:
        data: dict[str, Any] = {"node-1": "abc"}
        filters: dict[str, Any] = {"node-1": {"op": "eq", "val": "xyz"}}
        assert self.linker._tile_matches_filters(data, filters) is False

    def test_missing_node_in_data(self) -> None:
        data: dict[str, Any] = {"other-node": "abc"}
        filters: dict[str, Any] = {"node-1": {"op": "eq", "val": "abc"}}
        assert self.linker._tile_matches_filters(data, filters) is False

    def test_multiple_filters_all_match(self) -> None:
        data: dict[str, Any] = {"node-1": "abc", "node-2": 10}
        filters: dict[str, Any] = {
            "node-1": {"op": "eq", "val": "abc"},
            "node-2": {"op": "gt", "val": 5},
        }
        assert self.linker._tile_matches_filters(data, filters) is True

    def test_multiple_filters_one_fails(self) -> None:
        data: dict[str, Any] = {"node-1": "abc", "node-2": 3}
        filters: dict[str, Any] = {
            "node-1": {"op": "eq", "val": "abc"},
            "node-2": {"op": "gt", "val": 5},
        }
        assert self.linker._tile_matches_filters(data, filters) is False

    def test_empty_data(self) -> None:
        filters: dict[str, Any] = {"node-1": {"op": "eq", "val": "abc"}}
        assert self.linker._tile_matches_filters({}, filters) is False

    def test_empty_data_empty_filters(self) -> None:
        assert self.linker._tile_matches_filters({}, {}) is True

    def test_default_op_is_eq(self) -> None:
        data: dict[str, Any] = {"node-1": "abc"}
        filters: dict[str, Any] = {"node-1": {"val": "abc"}}
        assert self.linker._tile_matches_filters(data, filters) is True

    def test_none_value_in_data(self) -> None:
        data: dict[str, Any] = {"node-1": None}
        filters: dict[str, Any] = {"node-1": {"op": "eq", "val": "abc"}}
        assert self.linker._tile_matches_filters(data, filters) is False

    def test_first_filter_fails_short_circuits(self) -> None:
        data: dict[str, Any] = {"node-1": "wrong", "node-2": "correct"}
        filters: dict[str, Any] = {
            "node-1": {"op": "eq", "val": "expected"},
            "node-2": {"op": "eq", "val": "correct"},
        }
        assert self.linker._tile_matches_filters(data, filters) is False

    def test_data_has_extra_keys_beyond_filters(self) -> None:
        data: dict[str, Any] = {"node-1": "abc", "node-2": "xyz", "node-3": 99}
        filters: dict[str, Any] = {"node-1": {"op": "eq", "val": "abc"}}
        assert self.linker._tile_matches_filters(data, filters) is True

    def test_concept_uri_filter_in_tile(self) -> None:
        data: dict[str, Any] = {
            "node-1": [{"uri": "http://example.com/concept/1"}],
        }
        filters: dict[str, Any] = {
            "node-1": {"op": "eq", "val": [{"uri": "http://example.com/concept/1"}]},
        }
        assert self.linker._tile_matches_filters(data, filters) is True

    def test_concept_uri_filter_mismatch_in_tile(self) -> None:
        data: dict[str, Any] = {
            "node-1": [{"uri": "http://example.com/concept/1"}],
        }
        filters: dict[str, Any] = {
            "node-1": {"op": "eq", "val": [{"uri": "http://example.com/concept/99"}]},
        }
        assert self.linker._tile_matches_filters(data, filters) is False

    def test_mixed_concept_and_scalar_filters(self) -> None:
        data: dict[str, Any] = {
            "node-1": [{"uri": "http://example.com/concept/1"}],
            "node-2": 42,
        }
        filters: dict[str, Any] = {
            "node-1": {"op": "eq", "val": [{"uri": "http://example.com/concept/1"}]},
            "node-2": {"op": "gte", "val": 40},
        }
        assert self.linker._tile_matches_filters(data, filters) is True

    def test_filter_with_unknown_op(self) -> None:
        data: dict[str, Any] = {"node-1": "abc"}
        filters: dict[str, Any] = {"node-1": {"op": "regex", "val": "abc"}}
        assert self.linker._tile_matches_filters(data, filters) is False

    def test_many_filters_all_must_pass(self) -> None:
        data: dict[str, Any] = {f"node-{i}": i for i in range(10)}
        filters: dict[str, Any] = {
            f"node-{i}": {"op": "eq", "val": i} for i in range(10)
        }
        assert self.linker._tile_matches_filters(data, filters) is True

    def test_many_filters_last_one_fails(self) -> None:
        data: dict[str, Any] = {f"node-{i}": i for i in range(10)}
        filters: dict[str, Any] = {
            f"node-{i}": {"op": "eq", "val": i} for i in range(9)
        }
        filters["node-9"] = {"op": "eq", "val": 999}
        assert self.linker._tile_matches_filters(data, filters) is False
