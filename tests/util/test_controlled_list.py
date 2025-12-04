from django.test import TestCase
from unittest.mock import patch, MagicMock

from arches_controlled_lists.models import ListItem, ListItemValue
from bcap.util.controlled_list import get_hierarchy_for_list_item


class ControlledListTests(TestCase):
    def setUp(self):
        # Setup code can go here if needed
        pass

    @patch("arches_controlled_lists.models.ListItem.objects.get")
    @patch("arches_controlled_lists.models.ListItemValue.objects.filter")
    def test_get_hierarchy_for_list_item_two_levels(self, mock_filter, mock_get):
        """
        child -> parent
        Expect: ["Parent Label", "Child Label"]
        """
        # Create mock ListItem instances
        parent_item = MagicMock()
        parent_item.id = "parent-id"
        parent_item.parent = None  # Root of hierarchy

        child_item = MagicMock()
        child_item.id = "child-id"
        child_item.parent = parent_item

        # get() is only called once for the initial ID
        mock_get.return_value = child_item

        # Mock the label lookup chain:
        # ListItemValue.objects.filter(...).values_list(...).first()
        # Called once for child, once for parent
        mock_filter.return_value.values_list.return_value.first.side_effect = [
            "Child Label",
            "Parent Label",
        ]

        # Call the function
        result = get_hierarchy_for_list_item("child-id")

        # Assertions
        self.assertEqual(result, ["Parent Label", "Child Label"])
        mock_get.assert_called_once_with(id="child-id")
        self.assertEqual(mock_filter.call_count, 2)

    @patch("arches_controlled_lists.models.ListItem.objects.get")
    @patch("arches_controlled_lists.models.ListItemValue.objects.filter")
    def test_get_hierarchy_for_list_item_three_levels(self, mock_filter, mock_get):
        """
        grandchild -> parent -> grandparent
        Expect: ["Grandparent Label", "Parent Label", "Child Label"]
        """
        # Create mock ListItem instances
        grandparent_item = MagicMock()
        grandparent_item.id = "grandparent-id"
        grandparent_item.parent = None

        parent_item = MagicMock()
        parent_item.id = "parent-id"
        parent_item.parent = grandparent_item

        child_item = MagicMock()
        child_item.id = "child-id"
        child_item.parent = parent_item

        # get() is only called once for the initial ID
        mock_get.return_value = child_item

        # Called once per level: child, parent, grandparent
        mock_filter.return_value.values_list.return_value.first.side_effect = [
            "Child Label",
            "Parent Label",
            "Grandparent Label",
        ]

        # Call the function
        result = get_hierarchy_for_list_item("child-id")

        # child -> parent -> grandparent, then reversed
        self.assertEqual(
            result,
            ["Grandparent Label", "Parent Label", "Child Label"],
        )
        mock_get.assert_called_once_with(id="child-id")
        self.assertEqual(mock_filter.call_count, 3)

    @patch("arches_controlled_lists.models.ListItem.objects.get")
    def test_get_hierarchy_for_list_item_nonexistent(self, mock_get):
        """
        Non-existent ID should return an empty list.
        """
        # Simulate ListItem.DoesNotExist exception
        mock_get.side_effect = ListItem.DoesNotExist

        # Call the function with a non-existent ID
        result = get_hierarchy_for_list_item("non-existent-id")

        # Assertions
        self.assertEqual(result, [])
        mock_get.assert_called_once_with(id="non-existent-id")
