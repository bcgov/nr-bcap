"""Unit tests for the pure register-type helpers: the reference-value parsers
and the register-type derivation rules. These touch no database, so they run as
SimpleTestCase."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from bcap.util.register_type_api import (
    RegisterTypeApi,
    _extract_list_item_id,
    _extract_resource_instance_id,
    _resolve_hierarchy,
    calculate_register_types,
)

MODULE = "bcap.util.register_type_api"


def _row(class_name=None, type_name=None, subtype=None, descriptor=None):
    return {
        "class_name": class_name,
        "type_name": type_name,
        "subtype": subtype,
        "descriptor": descriptor,
    }


class ExtractListItemIdTests(SimpleTestCase):
    def test_none_and_empty_return_none(self):
        self.assertIsNone(_extract_list_item_id(None))
        self.assertIsNone(_extract_list_item_id([]))

    def test_prefers_label_list_item_id(self):
        value = [{"labels": [{"list_item_id": "abc-123"}], "uri": "x/y/z"}]
        self.assertEqual(_extract_list_item_id(value), "abc-123")

    def test_falls_back_to_last_uri_segment(self):
        value = [{"labels": [], "uri": "https://example.org/items/the-id/"}]
        self.assertEqual(_extract_list_item_id(value), "the-id")

    def test_string_item_inside_list(self):
        self.assertEqual(_extract_list_item_id(["plain-id"]), "plain-id")

    def test_bare_string_value(self):
        self.assertEqual(_extract_list_item_id("bare-id"), "bare-id")


class ExtractResourceInstanceIdTests(SimpleTestCase):
    def test_none_returns_empty(self):
        self.assertEqual(_extract_resource_instance_id(None), [])

    def test_collects_resource_ids_and_skips_malformed(self):
        value = [
            {"resourceId": "r1"},
            {"resourceId": "r2"},
            {"no_id": "skip"},
            "not-a-dict",
        ]
        self.assertEqual(_extract_resource_instance_id(value), ["r1", "r2"])

    def test_non_list_returns_empty(self):
        self.assertEqual(_extract_resource_instance_id("nope"), [])


class CalculateRegisterTypesTests(SimpleTestCase):
    def test_empty_inputs_yield_nothing(self):
        self.assertEqual(calculate_register_types([], []), [])

    def test_precontact_is_an_archaeological_site(self):
        self.assertEqual(
            calculate_register_types([_row(class_name="Precontact")], []),
            ["Archaeological Site"],
        )

    def test_ancestral_remains_also_flags_archaeological_site(self):
        result = calculate_register_types([_row(type_name="Human Remains")], [])
        self.assertEqual(result, ["Ancestral Remains", "Archaeological Site"])

    def test_rock_art_flags_site_and_rock_art(self):
        result = calculate_register_types([_row(subtype="Rock Art")], [])
        self.assertEqual(result, ["Archaeological Site", "Rock Art"])

    def test_shipwreck_flags_site_and_heritage_wreck(self):
        result = calculate_register_types([_row(descriptor="Shipwreck")], [])
        self.assertEqual(result, ["Archaeological Site", "Heritage Wreck"])

    def test_act_sections_map_to_register_types(self):
        self.assertEqual(
            calculate_register_types([], ["S. 4"]),
            ["S.4 Agreement with First Nations"],
        )
        self.assertEqual(
            calculate_register_types([], ["S. 11.1"]),
            ["Provincial Heritage Site or Object"],
        )

    def test_palaeontological_site(self):
        self.assertEqual(
            calculate_register_types([_row(class_name="Palaeontological")], []),
            ["Palaeontological Site"],
        )

    def test_postcontact_alone_is_unprotected_historic_site(self):
        self.assertEqual(
            calculate_register_types([_row(class_name="Postcontact")], []),
            ["Unprotected Historic Site"],
        )

    def test_postcontact_excluded_when_precontact_present(self):
        rows = [_row(class_name="Postcontact"), _row(class_name="Precontact")]
        result = calculate_register_types(rows, [])
        self.assertIn("Archaeological Site", result)
        self.assertNotIn("Unprotected Historic Site", result)

    def test_postcontact_excluded_by_human_remains_and_wreck(self):
        rows = [
            _row(class_name="Postcontact", type_name="Human Remains"),
            _row(descriptor="Airplane Wreck"),
        ]
        self.assertNotIn(
            "Unprotected Historic Site", calculate_register_types(rows, [])
        )


class ResolveHierarchyTests(SimpleTestCase):
    def test_walks_parents_and_orders_root_first(self):
        leaf = MagicMock()
        root = MagicMock()
        leaf.parent = root
        root.parent = None

        with (
            patch(f"{MODULE}.ListItem") as list_item,
            patch(f"{MODULE}.ListItemValue") as list_item_value,
        ):
            list_item.objects.filter.return_value.first.return_value = leaf
            # Labels resolved leaf-first; the function reverses to root-first.
            (
                list_item_value.objects.filter.return_value.values_list.return_value.first.side_effect
            ) = ["Site", "Precontact"]
            result = _resolve_hierarchy("leaf-id")

        self.assertEqual(result["class_name"], "Precontact")
        self.assertEqual(result["type_name"], "Site")
        self.assertIsNone(result["subtype"])


class RegisterTypeApiMethodTests(SimpleTestCase):
    def test_build_register_type_map_inverts_label_to_id(self):
        api = RegisterTypeApi()
        api._register_type_list_id = "list-1"
        with patch(f"{MODULE}.ListItemValue") as list_item_value:
            list_item_value.objects.filter.return_value.values_list.return_value = [
                ("Rock Art", "uuid-1"),
                ("Heritage Wreck", "uuid-2"),
            ]
            result = api._build_register_type_map()
        self.assertEqual(result, {"Rock Art": "uuid-1", "Heritage Wreck": "uuid-2"})

    def test_build_reference_value_skips_missing_items(self):
        api = RegisterTypeApi()
        item = MagicMock()
        item.uri = "https://example.org/items/uuid-1"
        item.list_id = "list-1"
        label = MagicMock()
        label.id = "lv-1"
        label.value = "Rock Art"
        label.language_id = "en"
        label.valuetype_id = "prefLabel"

        with (
            patch(f"{MODULE}.ListItem") as list_item,
            patch(f"{MODULE}.ListItemValue") as list_item_value,
        ):
            # First id resolves, second is missing and is skipped.
            list_item.objects.filter.return_value.first.side_effect = [item, None]
            list_item_value.objects.filter.return_value = [label]
            result = api._build_reference_value(["uuid-1", "uuid-2"])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["uri"], "https://example.org/items/uuid-1")
        self.assertEqual(result[0]["labels"][0]["list_item_id"], "uuid-1")
        self.assertEqual(result[0]["labels"][0]["value"], "Rock Art")
