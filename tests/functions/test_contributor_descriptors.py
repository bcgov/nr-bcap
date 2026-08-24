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

    def _name(self, values):
        return self._descriptor(DescriptorTypes.NAME, values)

    def _description(self, values):
        return self._descriptor(DescriptorTypes.DESCRIPTION, values)

    def test_full_name(self):
        self.assertEqual(self._name(["Smith", "Jane"]), "Smith, Jane")

    def test_organization_only(self):
        self.assertEqual(self._name(["Acme Consulting", None]), "Acme Consulting")

    def test_blank_first_name(self):
        self.assertEqual(self._name(["Smith", ""]), "Smith")

    def test_type_and_role(self):
        self.assertEqual(
            self._description(["Individual", "Author"]), "Individual, Author"
        )

    def test_type_without_role(self):
        self.assertEqual(self._description(["Organization", None]), "Organization")

    def test_map_popup_is_empty(self):
        self.assertEqual(self._descriptor(DescriptorTypes.MAP_POPUP, []), "")

    def test_aliases_used(self):
        self.assertEqual(nodes.NAME, [A.CONTRIBUTOR_NAME, A.FIRST_NAME])
        self.assertEqual(nodes.CARD, [A.CONTRIBUTOR_TYPE, A.CONTRIBUTOR_ROLE])
