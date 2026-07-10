from django.test import SimpleTestCase
from unittest.mock import MagicMock

from bcap.util.queryset import deep_get, filter_or_empty, first_pk


class FilterOrEmptyTests(SimpleTestCase):
    def setUp(self):
        self.qs = MagicMock()

    def test_all_values_present_calls_filter(self):
        filter_or_empty(self.qs, name="Alice", status="active")
        self.qs.filter.assert_called_once_with(name="Alice", status="active")

    def test_none_value_returns_none_queryset(self):
        result = filter_or_empty(self.qs, name=None)
        self.qs.none.assert_called_once()
        self.qs.filter.assert_not_called()
        self.assertEqual(result, self.qs.none.return_value)

    def test_empty_string_value_returns_none_queryset(self):
        filter_or_empty(self.qs, name="")
        self.qs.none.assert_called_once()
        self.qs.filter.assert_not_called()

    def test_mixed_empty_and_present_values_returns_none_queryset(self):
        filter_or_empty(self.qs, name="Alice", status=None)
        self.qs.none.assert_called_once()
        self.qs.filter.assert_not_called()

    def test_no_lookups_calls_filter_with_no_args(self):
        filter_or_empty(self.qs)
        self.qs.filter.assert_called_once_with()


class FirstPkTests(SimpleTestCase):
    def test_returns_pk_as_string_when_instance_exists(self):
        qs = MagicMock()
        qs.first.return_value.pk = 42
        self.assertEqual(first_pk(qs), "42")

    def test_returns_none_when_queryset_is_empty(self):
        qs = MagicMock()
        qs.first.return_value = None
        self.assertIsNone(first_pk(qs))


class DeepGetTests(SimpleTestCase):
    def test_single_key(self):
        self.assertEqual(deep_get({"a": 1}, "a"), 1)

    def test_nested_keys(self):
        obj = {"a": {"b": {"c": "found"}}}
        self.assertEqual(deep_get(obj, "a", "b", "c"), "found")

    def test_missing_top_level_key_returns_none(self):
        self.assertIsNone(deep_get({"a": 1}, "b"))

    def test_missing_nested_key_returns_none(self):
        self.assertIsNone(deep_get({"a": {"b": 1}}, "a", "c"))

    def test_non_dict_intermediate_returns_none(self):
        self.assertIsNone(deep_get({"a": "not-a-dict"}, "a", "b"))

    def test_no_keys_returns_obj(self):
        obj = {"a": 1}
        self.assertIs(deep_get(obj), obj)

    def test_none_obj_returns_none(self):
        self.assertIsNone(deep_get(None, "a"))
