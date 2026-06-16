"""Shared test support for resources built through ``ResourceBuilder``.

The contributor_type and hca_permit_type controlled lists the builder reads are
referenced by the graphs but not populated by the package load, so the builder
can't run until their list items exist. Any test that builds these resources
can seed the items from here."""

import uuid

from arches.app.models.models import Node

from arches_controlled_lists.models import List, ListItem, ListItemValue


class ControlledListFixtures:
    """Seed the minimal controlled-list items ``ResourceBuilder`` needs."""

    _ITEMS = [
        ("contributor", "contributor_type", "Archaeologist", 1),
        ("contributor", "contributor_type", "Consultant", 2),
        # The default type the invite flow assigns to a new Contributor.
        ("contributor", "contributor_type", "Individual", 3),
        ("hca_permit", "hca_permit_type", "Investigation", 1),
    ]

    @classmethod
    def seed(cls, register_cleanup=None):
        """Create the list items. Pass ``register_cleanup`` (eg
        ``TestCase.addCleanup``) to delete them afterward; omit it when the
        caller's transaction is rolled back for you (eg ``setUpTestData``)."""
        for slug, alias, label, sortorder in cls._ITEMS:
            cls._seed_item(slug, alias, label, sortorder, register_cleanup)

    @staticmethod
    def _seed_item(slug, alias, label, sortorder, register_cleanup):
        node = Node.objects.get(graph__slug=slug, alias=alias, source_identifier=None)
        list_id = node.config["controlledList"]
        controlled_list, created = List.objects.get_or_create(
            pk=list_id,
            defaults={"name": alias, "dynamic": False, "searchable": False},
        )
        if created and register_cleanup:
            register_cleanup(controlled_list.delete)
        item = ListItem.objects.create(
            id=uuid.uuid4(),
            list=controlled_list,
            sortorder=sortorder,
            uri=f"https://bcap.test/clm/{uuid.uuid4()}",
        )
        if register_cleanup:
            register_cleanup(item.delete)
        ListItemValue.objects.create(
            id=uuid.uuid4(),
            list_item=item,
            valuetype_id="prefLabel",
            language_id="en",
            value=label,
        )
        return item


class SeedControlledListsMixin:
    """Per-test seeding for ``TestCase`` classes that build the demo graph in
    ``setUp`` or test bodies."""

    def setUp(self):
        super().setUp()
        ControlledListFixtures.seed(self.addCleanup)
