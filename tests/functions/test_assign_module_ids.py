"""Unit tests for the assign-module-ids save hook. The ORM and node lookups are
mocked, so no database access is required. The full save-to-stamp path is
exercised end to end by the permit application API tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from bcap.functions.assign_module_ids import AssignModuleIds


# node_id(slug, alias) is mocked to return the alias, so tile.data keys below are
# just the alias strings.
def NODE_ID(_slug, alias):
    return alias


def _tile(data=None, pk="tile-pk"):
    return SimpleNamespace(data=data if data is not None else {}, pk=pk)


class SlugTests(SimpleTestCase):
    def test_uppercases_and_hyphenates(self):
        self.assertEqual(AssignModuleIds._slug("Site Assessment"), "SITE-ASSESSMENT")

    def test_collapses_runs_of_non_alphanumerics(self):
        self.assertEqual(AssignModuleIds._slug("A -- b__c"), "A-B-C")

    def test_strips_leading_and_trailing_separators(self):
        self.assertEqual(AssignModuleIds._slug("  hello!  "), "HELLO")

    def test_empty_and_none_become_empty_string(self):
        self.assertEqual(AssignModuleIds._slug(""), "")
        self.assertEqual(AssignModuleIds._slug(None), "")


@patch("bcap.functions.assign_module_ids.node_id", NODE_ID)
@patch("bcap.functions.assign_module_ids.localized_string", lambda value: value)
class SaveTests(SimpleTestCase):
    @patch.object(AssignModuleIds, "_next_sequence", return_value=48213)
    def test_mints_module_id_when_missing(self, _seq):
        tile = _tile({"module_name": "Investigation"})
        AssignModuleIds().save(tile, request=None)

        self.assertEqual(tile.data["module_id"], "INVESTIGATION-48213")
        self.assertEqual(tile._minted_module_id, "INVESTIGATION-48213")

    @patch.object(AssignModuleIds, "_next_sequence")
    def test_leaves_existing_module_id_untouched(self, seq):
        tile = _tile({"module_id": "INVESTIGATION-1", "module_name": "Investigation"})
        AssignModuleIds().save(tile, request=None)

        self.assertEqual(tile.data["module_id"], "INVESTIGATION-1")
        self.assertIsNone(tile._minted_module_id)
        seq.assert_not_called()


@patch("bcap.functions.assign_module_ids.node_id", NODE_ID)
class PostSaveTests(SimpleTestCase):
    def test_returns_early_when_nothing_was_minted(self):
        tile = _tile()
        tile._minted_module_id = None
        with patch.object(AssignModuleIds, "_stamp_requirement") as stamp:
            AssignModuleIds().post_save(tile, request=None)
        stamp.assert_not_called()

    @patch("bcap.functions.assign_module_ids.TileModel")
    def test_stamps_every_referenced_requirement_with_order(self, TileModel):
        tile = _tile(pk="parent-1")
        tile._minted_module_id = "INVESTIGATION-48213"
        child = SimpleNamespace(
            data={
                "process_requirement_order": 2,
                "process_requirement": [
                    {"resourceId": "req-a"},
                    {"resourceId": "req-b"},
                ],
            }
        )
        TileModel.objects.filter.return_value = [child]

        with patch.object(AssignModuleIds, "_stamp_requirement") as stamp:
            AssignModuleIds().post_save(tile, request=None)

        TileModel.objects.filter.assert_called_once_with(parenttile_id="parent-1")
        stamp.assert_any_call("req-a", "INVESTIGATION-48213", 2)
        stamp.assert_any_call("req-b", "INVESTIGATION-48213", 2)
        self.assertEqual(stamp.call_count, 2)


@patch("bcap.functions.assign_module_ids.node_id", NODE_ID)
@patch("bcap.functions.assign_module_ids.localized", lambda value: {"en": value})
@patch("bcap.functions.assign_module_ids.localized_string", lambda value: value)
class StampRequirementTests(SimpleTestCase):
    def test_no_requirement_id_is_a_noop(self):
        with patch("bcap.functions.assign_module_ids.TileModel") as TileModel:
            AssignModuleIds()._stamp_requirement(None, "INVESTIGATION-1", 1)
        TileModel.objects.filter.assert_not_called()

    @patch("bcap.functions.assign_module_ids.TileModel")
    def test_missing_identification_tile_is_a_noop(self, TileModel):
        TileModel.objects.filter.return_value.first.return_value = None
        # Should not raise even though there is no tile to stamp.
        AssignModuleIds()._stamp_requirement("req-1", "INVESTIGATION-1", 1)

    @patch("bcap.functions.assign_module_ids.TileModel")
    def test_writes_derived_id_and_saves_only_data(self, TileModel):
        tile = MagicMock()
        tile.data = {
            "requirement_name": "Site Assessment",
            "requirement_identification": "old",
        }
        TileModel.objects.filter.return_value.first.return_value = tile

        AssignModuleIds()._stamp_requirement("req-1", "INVESTIGATION-48213", 1)

        self.assertEqual(
            tile.data["requirement_identification"],
            {"en": "INVESTIGATION-48213-SITE-ASSESSMENT-001"},
        )
        tile.save.assert_called_once_with(update_fields=["data"])
