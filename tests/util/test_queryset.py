from django.test import SimpleTestCase
from unittest.mock import MagicMock

from bcap.util.queryset import filter_or_empty


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
