"""Low-level builders for creating bcap graph resources through
arches-querysets, so created data stays in sync with how the services read it.

Shared by the dashboard demo seeder (``dashboard_seed``) and the unit tests:
the seeder composes these into a full demo graph, while tests can use the
primitives to build just the resources a case needs."""

import uuid
import random
from dataclasses import dataclass

from django.utils import timezone

from arches.app.models.models import (
    GraphModel,
    Node,
    ResourceInstanceLifecycleState,
)

from arches_controlled_lists.models import ListItem
from arches_querysets.models import AliasedData, ResourceTileTree

# Marker written to legacyid of every resource the seeders create, so the
# clear command can find and delete only seeded data.
SEED_LEGACYID_PREFIX = "dashboard-seed"


class ResourceBuilder:
    """Create graph resources through arches-querysets.

    Holds the shared save state (lifecycle state, save kwargs, graphid cache) so
    one builder can create several resources."""

    def __init__(self):
        self.state = ResourceInstanceLifecycleState.objects.first()
        self.save_kwargs = {"force_admin": True, "partial": False, "index": False}
        self._graph_ids = {}

    @staticmethod
    def localized(value):
        """A `string` datatype value."""
        return {"en": {"value": value, "direction": "ltr"}}

    @staticmethod
    def reference_value(slug, alias, label=None):
        """A `reference` value from a node's controlled list: the item matching
        ``label``, or the first item if ``label`` is None."""
        node = Node.objects.get(graph__slug=slug, alias=alias, source_identifier=None)
        list_id = node.config.get("controlledList")
        items = ListItem.objects.filter(list_id=list_id)
        if label is not None:
            item = items.filter(list_item_values__value=label).first()
        else:
            item = items.order_by("sortorder").first()
        if item is None:
            raise RuntimeError(
                f"Controlled list {list_id} backing {slug}.{alias} has no "
                f"{'matching ' if label else ''}items; load its reference data first."
            )
        return [str(item.pk)]

    @staticmethod
    def random_reference_value(slug, alias):
        """A `reference` value: a randomly chosen item from the node's
        controlled list."""
        node = Node.objects.get(graph__slug=slug, alias=alias, source_identifier=None)
        list_id = node.config.get("controlledList")
        item_ids = list(
            ListItem.objects.filter(list_id=list_id).values_list("pk", flat=True)
        )
        if not item_ids:
            raise RuntimeError(
                f"Controlled list {list_id} backing {slug}.{alias} has no items; "
                "load its reference data first."
            )
        return [str(random.choice(item_ids))]

    @staticmethod
    def append_blank_tile_for_group(container, grouping_alias, values):
        """Append a blank tile for ``grouping_alias`` and set its node values by alias."""
        container.append_tile(grouping_alias)
        # One or many
        tile = getattr(container.aliased_data, grouping_alias)
        if isinstance(tile, list):
            tile = tile[-1]
        for alias, value in values.items():
            setattr(tile.aliased_data, alias, value)
        return tile

    def graph_id(self, slug):
        """Cache slug -> graphid; new_resource is called once per resource but
        there are only a handful of distinct graphs."""
        if slug not in self._graph_ids:
            self._graph_ids[slug] = GraphModel.objects.get(slug=slug).pk
        return self._graph_ids[slug]

    def new_resource(self, slug):
        """A fresh, unsaved ResourceTileTree. Its resource row is created on the
        first save(), as a side effect of saving its tiles, so callers must add
        at least one tile before saving."""
        resource = ResourceTileTree(
            graph_id=self.graph_id(slug),
            resource_instance_lifecycle_state=self.state,
            createdtime=timezone.now(),
            legacyid=f"{SEED_LEGACYID_PREFIX}:{uuid.uuid4()}",
        )
        resource.aliased_data = AliasedData()
        return resource

    def make_contributor(self, contributor_type, first_name, name):
        """``first_name`` is None for an organization."""
        contributor = self.new_resource("contributor")
        self.append_blank_tile_for_group(
            contributor,
            "contributor",
            {
                "first_name": self.localized(first_name) if first_name else None,
                "contributor_name": self.localized(name),
                "contributor_type": contributor_type,
            },
        )
        contributor.save(**self.save_kwargs)
        return contributor

    def make_process_requirement(self, spec):
        """Create and return a process requirement resource."""
        requirement = self.new_resource("process_requirement")
        # requirement_identification is a grouping node that also holds a required value.
        self.append_blank_tile_for_group(
            requirement,
            "requirement_identification",
            {
                "requirement_identification": self.localized(spec["id"]),
                "requirement_name": self.localized(spec["name"]),
            },
        )
        self.append_blank_tile_for_group(
            requirement,
            "requirement_execution_duration",
            {"requirement_process_due_date": spec["due"]},
        )
        self.append_blank_tile_for_group(
            requirement,
            "sub_requirement_assessment_n1",
            {
                "requirement_status": spec["satisfied"],
                "assessment_notes": self.localized(spec["notes"]),
            },
        )
        for sub in spec["sub_requirements"]:
            self.append_blank_tile_for_group(
                requirement,
                "sub_requirement",
                {
                    "sub_requirement_name": self.localized(sub["name"]),
                    "sub_requirement_description": self.localized(sub["description"]),
                    "sub_requirement_satisfied": sub["sub_satisfied"],
                    "sub_requirement_sort_order": sub["sort_order"],
                },
            )
        requirement.save(**self.save_kwargs)
        return requirement
