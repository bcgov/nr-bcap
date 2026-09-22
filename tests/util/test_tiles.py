from types import SimpleNamespace

from django.db.models import Q
from django.test import SimpleTestCase

from bcap.util.tiles import (
    payload_resource_id,
    referenced_resource_ids,
    references_any,
    set_payload_node,
)


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


class PayloadNodeTests(SimpleTestCase):
    def test_reads_back_a_written_reference(self):
        payload = {}
        set_payload_node(payload, "group", "node", [{"resourceId": "a"}])
        self.assertEqual(payload_resource_id(payload, "group", "node"), "a")

    def test_reads_a_bare_reference(self):
        payload = {}
        set_payload_node(payload, "group", "node", {"resourceId": "a"})
        self.assertEqual(payload_resource_id(payload, "group", "node"), "a")

    def test_absent_or_malformed_reads_as_none(self):
        for payload in ({}, {"aliased_data": "junk"}, {"aliased_data": {"group": 1}}):
            with self.subTest(payload=payload):
                self.assertIsNone(payload_resource_id(payload, "group", "node"))


class ReferencesAnyTests(SimpleTestCase):
    def test_no_ids_matches_nothing(self):
        # An unscoped Q() would match every tile.
        self.assertEqual(references_any("node", []), Q(pk__in=[]))
