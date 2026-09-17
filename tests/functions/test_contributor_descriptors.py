from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from bcap.functions.contributor_descriptors import (
    ContributorDescriptorNodes as nodes,
    ContributorDescriptors,
)
from bcap.util.aliases.contributor import ContributorAliases as A
from bcap.util.descriptors import DescriptorTypes


class ContributorDescriptorsTests(SimpleTestCase):
    def _descriptor(self, descriptor, values):
        with (
            patch.object(ContributorDescriptors, "_graph_lookup", MagicMock()),
            patch.object(
                ContributorDescriptors,
                "get_value_from_node",
                side_effect=lambda node, datatype, resource, context=None: values.pop(
                    0
                ),
            ),
        ):
            return ContributorDescriptors().get_primary_descriptor_from_nodes(
                MagicMock(), {}, descriptor=descriptor
            )

    def test_descriptors(self):
        for descriptor, values, expected in (
            (DescriptorTypes.NAME, ["Smith", "Jane"], "Smith, Jane"),
            (DescriptorTypes.NAME, ["Acme Consulting", None], "Acme Consulting"),
            (DescriptorTypes.NAME, ["Smith", ""], "Smith"),
            (
                DescriptorTypes.DESCRIPTION,
                ["Individual", "Author"],
                "Individual, Author",
            ),
            (DescriptorTypes.DESCRIPTION, ["Organization", None], "Organization"),
            (DescriptorTypes.MAP_POPUP, [], ""),
        ):
            with self.subTest(f"{descriptor} {values}"):
                self.assertEqual(self._descriptor(descriptor, values), expected)

    def test_aliases_used(self):
        self.assertEqual(nodes.NAME, [A.CONTRIBUTOR_NAME, A.FIRST_NAME])
        self.assertEqual(nodes.CARD, [A.CONTRIBUTOR_TYPE, A.CONTRIBUTOR_ROLE])
