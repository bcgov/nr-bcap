from django.test import SimpleTestCase

from bcap.util.dicts import deep_get


class DeepGetTests(SimpleTestCase):
    def test_deep_get(self):
        obj = {"a": 1}
        nested = {"a": {"b": {"c": "found"}}}
        self.assertEqual(deep_get({"a": 1}, "a"), 1)  # single key
        self.assertEqual(deep_get(nested, "a", "b", "c"), "found")  # nested keys
        self.assertIsNone(deep_get({"a": 1}, "b"))  # missing top-level key
        self.assertIsNone(deep_get({"a": {"b": 1}}, "a", "c"))  # missing nested key
        self.assertIsNone(
            deep_get({"a": "not-a-dict"}, "a", "b")
        )  # non-dict on the way
        self.assertIs(deep_get(obj), obj)  # no keys returns the object
        self.assertIsNone(deep_get(None, "a"))  # None object
