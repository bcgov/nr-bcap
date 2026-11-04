"""Generic primitives for creating bcap graph resources through arches-querysets,
so created data stays in sync with how the services read it. The domain builders
(contributor, process requirement) extend this base."""

import uuid
from contextlib import contextmanager
from copy import deepcopy

from django.utils import timezone

from django.contrib.auth import get_user_model

from arches.app.models.models import (
    ResourceInstance,
    ResourceInstanceLifecycleState,
)
from arches.app.models.resource import Resource
from arches.app.models.tile import Tile

from bcap.util.i18n import localized
from bcap.util.save import acting_request

from arches_querysets.models import (
    AliasedData,
    GraphWithPrefetching,
    ResourceTileTree,
)

# Marker written to legacyid of every resource the seeders create, so the
# clear command can find and delete only seeded data.
SEED_LEGACYID_PREFIX = "dashboard-seed"


class ResourceBuilder:
    """Create graph resources through arches-querysets.

    Holds the shared save state (lifecycle state, save kwargs, graphid cache) so
    one builder can create several resources."""

    # Tag with the seed legacyid so clear_dashboard_data finds it; real route
    # data passes tag_as_seed=False to be left alone.
    _TAG_AS_SEED = True

    def __init__(self, skip_refresh=True, owner=None, tag_as_seed=None, request=None):
        if tag_as_seed is not None:
            self._TAG_AS_SEED = tag_as_seed
        self.state = ResourceInstanceLifecycleState.objects.first()
        self.request = acting_request(request)
        # The tile-first save never sets principaluser, so claim() does it later.
        self.owner = owner or self.request.user
        self._save_as = {"request": self.request}
        self.save_kwargs = {**self._save_as, "partial": False, "index": False}
        self._graphs = {}
        # save() re-runs get_tiles() to rehydrate aliased_data (~70% of cost);
        # builders only need the saved rows.
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

    localized = staticmethod(localized)

    @staticmethod
    def append_blank_tile_for_group(container, grouping_alias, values):
        """Append a blank tile for the group and set its node values by alias."""
        container.append_tile(grouping_alias)
        tile = getattr(container.aliased_data, grouping_alias)
        if isinstance(tile, list):
            tile = tile[-1]
        for alias, value in values.items():
            setattr(tile.aliased_data, alias, value)
        return tile

    @staticmethod
    def prune_blank_tiles(container, grouping_alias, marker_alias=None):
        """Drop the blank tile arches auto-creates for a group when its parent
        tile is appended. With a marker alias, keep the tiles whose marker node
        has a value; without one, drop them all (the caller appends the real
        tiles next)."""
        tiles = getattr(container.aliased_data, grouping_alias) or []
        kept = (
            [t for t in tiles if getattr(t.aliased_data, marker_alias)]
            if marker_alias is not None
            else []
        )
        setattr(container.aliased_data, grouping_alias, kept)

    def graph(self, slug):
        """Cache slug -> a graph with nodes/nodegroups/cards/widgets prefetched.

        append_tile() and save() re-read the graph and its metadata on an
        unsealed resource (~40 of the ~110 queries per save). Sealing one
        prefetched graph onto every resource of a slug shares that single load."""
        if slug not in self._graphs:
            self._graphs[slug] = GraphWithPrefetching.objects.prefetch(
                graph_slug=slug
            ).get()
        return self._graphs[slug]

    def graph_id(self, slug):
        return self.graph(slug).pk

    def claim(self, resource):
        """Set principaluser (the creating user); the tile-first save skips it."""
        ResourceInstance.objects.filter(pk=resource.pk).update(principaluser=self.owner)

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

    @staticmethod
    def set_node_value(resource, nodeid, value):
        """Set a node's value directly in tile data, on whichever of a resource's
        loaded tiles holds it (a write by node id, bypassing aliased_data)."""
        for tile in resource.tiles:
            if nodeid in tile.data:
                tile.data[nodeid] = value

    @staticmethod
    def copy_resource(source):
        """A new, unsaved resource with the source's tiles rebuilt under fresh
        GUIDs (from the model defaults), node data deep-copied, and parent links
        repointed at the new tiles."""
        # By hand rather than Resource.copy(): copy() is broken on arches 8.1.x
        # (passes a string context where a dict is expected). Fixed in 8.2 by
        # PR#12695.
        new_resource = Resource()
        new_resource.graph = source.graph
        copies = {}
        for tile in source.tiles:
            new_tile = Tile()
            new_tile.data = deepcopy(tile.data)
            new_tile.nodegroup = tile.nodegroup
            new_tile.resourceinstance = new_resource
            new_tile.sortorder = tile.sortorder
            new_tile.tiles = []
            copies[tile.pk] = new_tile
        for tile in source.tiles:
            if tile.parenttile_id:
                copies[tile.pk].parenttile = copies[tile.parenttile_id]
        new_resource.tiles = list(copies.values())
        return new_resource
