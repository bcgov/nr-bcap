"""
Shared scaffolding for the primary-descriptor unit tests.

The three descriptors share a base that caches nodes and datatypes on the class
and reads tiles through the ORM. These stub both so the tests exercise the
descriptor's own logic without a database.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from django.test import TestCase


def make_node(name, nodegroup_id="ng-1", nodeid="node-1"):
    node = MagicMock()
    node.name = name
    node.nodegroup_id = nodegroup_id
    node.nodeid = nodeid
    return node


def make_tile(data=None):
    tile = MagicMock()
    tile.data = data if data is not None else {}
    return tile


class DescriptorTestCase(TestCase):
    """Seeds the class-level node caches and stubs the one ORM reader every
    descriptor goes through. Tests drive it by assigning to self.values, and
    read back self.reads to assert which aliases were walked, in order."""

    descriptor_class: Any = None
    # alias -> the node's display name, which the descriptor uses as the label.
    node_names: dict[str, str] = {}

    def setUp(self):
        cls = self.descriptor_class
        cls._initialized = True  # skip initialize()
        cls._nodes = {alias: make_node(name) for alias, name in self.node_names.items()}
        cls._datatypes = {alias: MagicMock() for alias in self.node_names}
        cls._html_nodes = []
        self.fn = cls()

        self.values: dict[str, str | None] = {}
        self.reads: list[str] = []

        def read(node_alias, *args, **kwargs):
            self.reads.append(node_alias)
            return self.values.get(node_alias)

        self.stub("_get_value_from_node", side_effect=read)
        self.addCleanup(self.reset)

    def stub(self, attribute, **kwargs):
        """Patch an attribute on the descriptor class for the test's lifetime."""
        patcher = patch.object(self.descriptor_class, attribute, **kwargs)
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        return mock

    def reset(self):
        cls = self.descriptor_class
        cls._initialized = False
        cls._nodes = {}
        cls._datatypes = {}
        cls._html_nodes = []

    def describe(self, descriptor="description", **config):
        return self.fn.get_primary_descriptor_from_nodes(
            MagicMock(),
            config={"first_only": False, "show_name": True, **config},
            descriptor=descriptor,
        )
