from __future__ import annotations

from bcap.search_components.cross_model_advanced_search import NodeValue


class TestNodeValue:
    def test_extract_single_dict(self) -> None:
        nv = NodeValue(raw={"resourceId": "abc-123"})
        assert nv.extract() == {"abc-123"}

    def test_extract_list_of_dicts(self) -> None:
        nv = NodeValue(
            raw=[
                {"resourceId": "abc-123"},
                {"resourceId": "def-456"},
            ]
        )
        assert nv.extract() == {"abc-123", "def-456"}

    def test_extract_empty_list(self) -> None:
        nv = NodeValue(raw=[])
        assert nv.extract() == set()

    def test_extract_none(self) -> None:
        nv = NodeValue(raw=None)
        assert nv.extract() == set()

    def test_extract_ignores_non_dict_items(self) -> None:
        nv = NodeValue(raw=["not-a-dict", 123, None])
        assert nv.extract() == set()

    def test_extract_ignores_dicts_without_resource_id(self) -> None:
        nv = NodeValue(raw=[{"otherId": "abc"}, {"resourceId": "def-456"}])
        assert nv.extract() == {"def-456"}

    def test_extract_mixed_valid_and_invalid(self) -> None:
        nv = NodeValue(
            raw=[
                {"resourceId": "abc-123"},
                {"somethingElse": "xyz"},
                None,
            ]
        )
        assert nv.extract() == {"abc-123"}

    def test_extract_string_raw(self) -> None:
        nv = NodeValue(raw="just-a-string")
        assert nv.extract() == set()

    def test_extract_integer_raw(self) -> None:
        nv = NodeValue(raw=42)
        assert nv.extract() == set()

    def test_extract_boolean_raw(self) -> None:
        nv = NodeValue(raw=True)
        assert nv.extract() == set()

    def test_extract_empty_dict(self) -> None:
        nv = NodeValue(raw={})
        assert nv.extract() == set()

    def test_extract_dict_with_extra_keys(self) -> None:
        nv = NodeValue(raw={"resourceId": "abc-123", "otherField": "xyz"})
        assert nv.extract() == {"abc-123"}

    def test_extract_duplicate_resource_ids(self) -> None:
        nv = NodeValue(
            raw=[
                {"resourceId": "abc-123"},
                {"resourceId": "abc-123"},
            ]
        )
        assert nv.extract() == {"abc-123"}

    def test_extract_list_of_empty_dicts(self) -> None:
        nv = NodeValue(raw=[{}, {}, {}])
        assert nv.extract() == set()

    def test_extract_nested_list_ignored(self) -> None:
        nv = NodeValue(raw=[[{"resourceId": "abc"}]])
        assert nv.extract() == set()

    def test_extract_false_raw(self) -> None:
        nv = NodeValue(raw=False)
        assert nv.extract() == set()

    def test_extract_zero_raw(self) -> None:
        nv = NodeValue(raw=0)
        assert nv.extract() == set()

    def test_extract_resource_id_is_none_still_extracted(self) -> None:
        nv = NodeValue(raw={"resourceId": None})
        assert nv.extract() == {None}

    def test_extract_resource_id_empty_string_still_extracted(self) -> None:
        nv = NodeValue(raw={"resourceId": ""})
        assert nv.extract() == {""}

    def test_extract_resource_id_is_integer(self) -> None:
        nv = NodeValue(raw={"resourceId": 42})
        assert nv.extract() == {42}

    def test_extract_large_list(self) -> None:
        items = [{"resourceId": f"id-{i}"} for i in range(100)]
        nv = NodeValue(raw=items)
        assert len(nv.extract()) == 100

    def test_extract_float_raw(self) -> None:
        nv = NodeValue(raw=3.14)
        assert nv.extract() == set()

    def test_extract_tuple_raw(self) -> None:
        nv = NodeValue(raw=({"resourceId": "abc"},))
        assert nv.extract() == set()

    def test_extract_dict_with_resource_id_key_case_sensitive(self) -> None:
        nv = NodeValue(raw={"ResourceId": "abc-123"})
        assert nv.extract() == set()

    def test_extract_dict_with_resourceid_lowercase(self) -> None:
        nv = NodeValue(raw={"resourceid": "abc-123"})
        assert nv.extract() == set()

    def test_extract_list_with_only_none_values(self) -> None:
        nv = NodeValue(raw=[None, None, None])
        assert nv.extract() == set()

    def test_extract_list_with_mixed_nones_and_valid(self) -> None:
        nv = NodeValue(raw=[None, {"resourceId": "abc"}, None])
        assert nv.extract() == {"abc"}

    def test_extract_set_raw(self) -> None:
        nv = NodeValue(raw={"a", "b"})
        assert nv.extract() == set()
