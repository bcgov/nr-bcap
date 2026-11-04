from __future__ import annotations

import pytest
from typing_extensions import Any

from bcap.search_components.cross_model_advanced_search import NodeValue


class TestNodeValue:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            pytest.param({"resourceId": "abc-123"}, {"abc-123"}, id="single_dict"),
            pytest.param(
                {"resourceId": "abc-123", "otherField": "xyz"},
                {"abc-123"},
                id="dict_with_extra_keys",
            ),
            pytest.param(
                {"resourceId": None}, {None}, id="resource_id_is_none_still_extracted"
            ),
            pytest.param(
                {"resourceId": ""}, {""}, id="resource_id_empty_string_still_extracted"
            ),
            pytest.param({"resourceId": 42}, {42}, id="resource_id_is_integer"),
            pytest.param(
                {"ResourceId": "abc-123"},
                set(),
                id="dict_with_resource_id_key_case_sensitive",
            ),
            pytest.param(
                {"resourceid": "abc-123"}, set(), id="dict_with_resourceid_lowercase"
            ),
            pytest.param({}, set(), id="empty_dict"),
            pytest.param(
                [{"resourceId": "abc-123"}, {"resourceId": "def-456"}],
                {"abc-123", "def-456"},
                id="list_of_dicts",
            ),
            pytest.param(
                [{"resourceId": "abc-123"}, {"resourceId": "abc-123"}],
                {"abc-123"},
                id="duplicate_resource_ids",
            ),
            pytest.param(
                [{"otherId": "abc"}, {"resourceId": "def-456"}],
                {"def-456"},
                id="ignores_dicts_without_resource_id",
            ),
            pytest.param(
                [{"resourceId": "abc"}, {"somethingElse": "xyz"}, None],
                {"abc"},
                id="mixed_valid_and_invalid",
            ),
            pytest.param(
                [None, {"resourceId": "abc"}, None],
                {"abc"},
                id="list_with_mixed_nones_and_valid",
            ),
            pytest.param(["not-a-dict", 123, None], set(), id="ignores_non_dict_items"),
            pytest.param([None, None, None], set(), id="list_with_only_none_values"),
            pytest.param([{}, {}, {}], set(), id="list_of_empty_dicts"),
            pytest.param([[{"resourceId": "abc"}]], set(), id="nested_list_ignored"),
            pytest.param([], set(), id="empty_list"),
            pytest.param(None, set(), id="none"),
            pytest.param("just-a-string", set(), id="string_raw"),
            pytest.param(42, set(), id="integer_raw"),
            pytest.param(3.14, set(), id="float_raw"),
            pytest.param(True, set(), id="boolean_raw"),
            pytest.param(False, set(), id="false_raw"),
            pytest.param(0, set(), id="zero_raw"),
            pytest.param(({"resourceId": "abc"},), set(), id="tuple_raw"),
            pytest.param({"a", "b"}, set(), id="set_raw"),
        ],
    )
    def test_extract(self, raw: Any, expected: set) -> None:
        assert NodeValue(raw=raw).extract() == expected
