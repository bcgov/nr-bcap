from django.test import TestCase

from arches.app.models.models import Node

from arches_controlled_lists.models import ListItemValue

from tests.controlled_list_fixtures import ControlledListFixtures


class ControlledListFixturesTests(TestCase):
    """ControlledListFixtures.seed() inserts the controlled-list items the
    resource builder reads but the package load doesn't provide."""

    def test_seed_inserts_each_configured_item(self):
        ControlledListFixtures.seed(self.addCleanup)

        for slug, alias, label, _sortorder in ControlledListFixtures._ITEMS:
            node = Node.objects.get(
                graph__slug=slug, alias=alias, source_identifier=None
            )
            list_id = node.config["controlledList"]
            self.assertTrue(
                ListItemValue.objects.filter(
                    list_item__list_id=list_id, value=label
                ).exists(),
                f"expected a seeded {label!r} item for {slug}.{alias}",
            )
