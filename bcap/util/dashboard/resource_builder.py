"""Low-level builders for creating bcap graph resources through
arches-querysets, so created data stays in sync with how the services read it.

Shared by the dashboard demo seeder (``dashboard_seed``) and the unit tests:
the seeder composes these into a full demo graph, while tests can use the
primitives to build just the resources a case needs."""

import uuid
import random
from contextlib import contextmanager
from dataclasses import dataclass

from django.utils import timezone

from arches.app.models.models import (
    Node,
    ResourceInstanceLifecycleState,
)
from arches.app.models.tile import Tile

from arches_controlled_lists.models import ListItem
from arches_querysets.models import (
    AliasedData,
    GraphWithPrefetching,
    ResourceTileTree,
)

# Marker written to legacyid of every resource the seeders create, so the
# clear command can find and delete only seeded data.
SEED_LEGACYID_PREFIX = "dashboard-seed"


@dataclass
class ContributorSpec:
    """Fields for a contributor resource."""

    contributor_type: object
    first_name: object  # None for an organization
    name: object
    bcap_username: object = None  # maps the contributor to a BCAP user
    associated_organization: object = None  # the organization it belongs to
    inactive: object = None  # the inactive flag on the contributor tile
    start_date: object = None  # membership start on the associated_organization tile
    end_date: object = None  # membership end on the associated_organization tile


class ResourceBuilder:
    """Create graph resources through arches-querysets.

    Holds the shared save state (lifecycle state, save kwargs, graphid cache) so
    one builder can create several resources."""

    # Tag created resources with the seed legacyid so clear_dashboard_data can
    # find and delete them.
    _TAG_AS_SEED = True

    def __init__(self, skip_refresh=True):
        self.state = ResourceInstanceLifecycleState.objects.first()
        self.save_kwargs = {"force_admin": True, "partial": False, "index": False}
        self._graphs = {}
        # save() re-runs the full get_tiles() query afterwards to rehydrate
        # aliased_data -- ~70% of the save cost. Builders only need the saved pk
        # (and persisted rows), so this is skipped by default. Pass
        # skip_refresh=False if a caller needs the refreshed tree back.
        self.skip_refresh = skip_refresh

    @contextmanager
    def deferred_descriptors(self):
        """Skip the per-tile descriptor function; save() recomputes the
        descriptor once per resource anyway, so displaynames are unchanged."""
        pre_save = Tile._Tile__preSave
        post_save = Tile._Tile__postSave
        Tile._Tile__preSave = lambda *args, **kwargs: None
        Tile._Tile__postSave = lambda *args, **kwargs: None
        try:
            yield
        finally:
            Tile._Tile__preSave = pre_save
            Tile._Tile__postSave = post_save

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

    def graph(self, slug):
        """Cache slug -> a graph with nodes/nodegroups/cards/widgets prefetched.

        append_tile() and save() both read ``resource.graph.node_set`` (and the
        graph publication); on an unsealed resource that re-queries the graph and
        all its metadata every call -- ~40 of the ~110 queries per save. Sealing
        one prefetched graph onto every resource of a slug (the same object
        get_tiles() attaches) lets all of them share that single load."""
        if slug not in self._graphs:
            self._graphs[slug] = GraphWithPrefetching.objects.prefetch(
                graph_slug=slug
            ).get()
        return self._graphs[slug]

    def graph_id(self, slug):
        return self.graph(slug).pk

    def new_resource(self, slug):
        """A fresh, unsaved ResourceTileTree. Its resource row is created on the
        first save(), as a side effect of saving its tiles, so callers must add
        at least one tile before saving."""
        graph = self.graph(slug)
        resource = ResourceTileTree(
            graph_id=graph.pk,
            resource_instance_lifecycle_state=self.state,
            createdtime=timezone.now(),
            legacyid=(
                f"{SEED_LEGACYID_PREFIX}:{uuid.uuid4()}" if self._TAG_AS_SEED else None
            ),
        )
        resource.aliased_data = AliasedData()
        # Reuse the prefetched graph instead of letting each append_tile/save
        # reload it; sealed=True tells arches-querysets it is already prefetched.
        resource.graph = graph
        resource.sealed = True
        if self.skip_refresh:
            resource.refresh_from_db = lambda *args, **kwargs: None
        return resource

    def make_contributor(self, spec):
        """Create and return a contributor resource from a ``ContributorSpec``."""
        contributor = self.new_resource("contributor")
        contributor_tile = self.append_blank_tile_for_group(
            contributor,
            "contributor",
            {
                "first_name": (
                    self.localized(spec.first_name) if spec.first_name else None
                ),
                "contributor_name": self.localized(spec.name),
                "contributor_type": spec.contributor_type,
                "bcap_username": spec.bcap_username,
                "inactive": spec.inactive,
            },
        )
        if spec.associated_organization is not None:
            self.append_blank_tile_for_group(
                contributor_tile,
                "associated_organization",
                {
                    "associated_organization": spec.associated_organization,
                    "start_date": spec.start_date,
                    "end_date": spec.end_date,
                },
            )
        contributor.save(**self.save_kwargs)
        return contributor

    def make_process_requirement(self, spec):
        """Create and return a process requirement resource."""
        requirement = self.new_resource("process_requirement")
        # requirement_identification is a grouping node that also holds a required value.
        identification = self.append_blank_tile_for_group(
            requirement,
            "requirement_identification",
            {
                "requirement_identification": self.localized(spec["id"]),
                "requirement_name": self.localized(spec["name"]),
            },
        )
        # is_template_requirement is a cardinality-1 child nodegroup of
        # requirement_identification, auto-created blank with the parent. Set the
        # flag on that child; a top-level append would leave the value on an
        # orphan tile while the real child kept its node default.
        identification.aliased_data.is_template_requirement.aliased_data.is_template_requirement = spec.get(
            "is_template", False
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
                    "sub_requirement_mandatory": sub.get("mandatory", False),
                    "sub_requirement_satisfied": sub["sub_satisfied"],
                    "sub_requirement_sort_order": sub["sort_order"],
                },
            )
        requirement.save(**self.save_kwargs)
        return requirement
