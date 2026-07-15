from types import SimpleNamespace

from django.test import SimpleTestCase

from bcap.util.tiles import referenced_resource_ids


def _tile(data):
    return SimpleNamespace(data=data)


class ReferencedResourceIdsTests(SimpleTestCase):
    NODE = "node-1"

    def test_collects_resource_ids_across_tiles(self):
        tiles = [
            _tile({self.NODE: [{"resourceId": "a"}, {"resourceId": "b"}]}),
            _tile({self.NODE: [{"resourceId": "c"}]}),
        ]
        self.assertEqual(referenced_resource_ids(tiles, self.NODE), {"a", "b", "c"})

    def test_deduplicates_repeated_ids(self):
        tiles = [
            _tile({self.NODE: [{"resourceId": "a"}]}),
            _tile({self.NODE: [{"resourceId": "a"}]}),
        ]
        self.assertEqual(referenced_resource_ids(tiles, self.NODE), {"a"})

    def test_ignores_absent_node_and_null_value(self):
        tiles = [_tile({}), _tile({self.NODE: None})]
        self.assertEqual(referenced_resource_ids(tiles, self.NODE), set())

    def test_skips_references_without_a_resource_id(self):
        tiles = [_tile({self.NODE: [{"resourceId": ""}, {"other": "x"}]})]
        self.assertEqual(referenced_resource_ids(tiles, self.NODE), set())
