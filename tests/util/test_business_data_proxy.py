"""Unit tests for the shared value-extraction logic on the business data proxy.
The graph lookup and tile manager are mocked, so no database is needed: the
tests pin down the boolean-label, language, and single/multi/empty result
branches of get_value_from_node."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from bcap.util.business_data_proxy import BusinessDataProxy

MODULE = "bcap.util.business_data_proxy"
NODE_ID = "11111111-1111-1111-1111-111111111111"


def _proxy(node, datatype):
    """A proxy with its graph lookup stubbed, skipping the DB-backed init."""
    proxy = BusinessDataProxy.__new__(BusinessDataProxy)
    proxy._graph_lookup = MagicMock()
    proxy._graph_lookup.get_node.return_value = node
    proxy._graph_lookup.get_datatype.return_value = datatype
    return proxy


def _string_node(datatype_name="string"):
    node = MagicMock()
    node.datatype = datatype_name
    node.nodeid = NODE_ID
    return node


class GetValueFromNodeTests(SimpleTestCase):
    def test_missing_node_or_datatype_returns_none(self):
        self.assertIsNone(_proxy(None, MagicMock()).get_value_from_node("a"))
        self.assertIsNone(_proxy(MagicMock(), None).get_value_from_node("a"))

    def test_single_display_value_from_data_tile(self):
        datatype = MagicMock()
        datatype.get_display_value.return_value = "Site A"
        proxy = _proxy(_string_node(), datatype)

        result = proxy.get_value_from_node("name", data_tile=MagicMock())

        self.assertEqual(result, "Site A")

    def test_multiple_tiles_return_a_list(self):
        datatype = MagicMock()
        datatype.get_display_value.side_effect = ["A", "B"]
        proxy = _proxy(_string_node(), datatype)

        with patch(f"{MODULE}.models") as models:
            qs = models.TileModel.objects.filter.return_value.filter
            qs.return_value = [MagicMock(), MagicMock()]
            result = proxy.get_value_from_node("name", resourceinstanceid="r1")

        self.assertEqual(result, ["A", "B"])

    def test_no_tiles_returns_none(self):
        proxy = _proxy(_string_node(), MagicMock())
        with patch(f"{MODULE}.models") as models:
            models.TileModel.objects.filter.return_value.filter.return_value = []
            self.assertIsNone(
                proxy.get_value_from_node("name", resourceinstanceid="r1")
            )

    def test_boolean_true_uses_true_label(self):
        node = MagicMock()
        node.datatype = "boolean"
        node.nodeid = NODE_ID
        node.config = {"trueLabel": {"en": "Yes"}, "falseLabel": {"en": "No"}}
        datatype = MagicMock()
        datatype.get_tile_data.return_value = {NODE_ID: True}
        proxy = _proxy(node, datatype)

        result = proxy.get_value_from_node(
            "flag", data_tile=MagicMock(), context={"language": "en"}
        )

        self.assertEqual(result, "Yes")

    def test_boolean_false_uses_false_label(self):
        node = MagicMock()
        node.datatype = "boolean"
        node.nodeid = NODE_ID
        node.config = {"trueLabel": {"en": "Yes"}, "falseLabel": {"en": "No"}}
        datatype = MagicMock()
        datatype.get_tile_data.return_value = {NODE_ID: False}
        proxy = _proxy(node, datatype)

        result = proxy.get_value_from_node(
            "flag", data_tile=MagicMock(), context={"language": "en"}
        )

        self.assertEqual(result, "No")

    def test_boolean_none_value_returns_none(self):
        node = MagicMock()
        node.datatype = "boolean"
        node.nodeid = NODE_ID
        node.config = {"trueLabel": {"en": "Yes"}, "falseLabel": {"en": "No"}}
        datatype = MagicMock()
        datatype.get_tile_data.return_value = {NODE_ID: None}
        proxy = _proxy(node, datatype)

        self.assertIsNone(proxy.get_value_from_node("flag", data_tile=MagicMock()))
