"""Low-level builders for creating bcap graph resources through
arches-querysets, so created data stays in sync with how the services read it.

Shared by the dashboard demo seeder (``dashboard_seed``) and the unit tests:
the seeder composes these into a full demo graph, while tests can use the
primitives to build just the resources a case needs."""

import uuid
import random
from contextlib import contextmanager

from django.utils import timezone

from arches.app.models.models import (
    EditLog,
    Node,
    ResourceInstanceLifecycleState,
)
from arches.app.models.resource import Resource
from arches.app.models.system_settings import settings as arches_settings
from arches.app.models.tile import Tile
from arches.app.utils.permission_backend import _get_permission_framework

from arches_controlled_lists.models import ListItem
from arches_querysets.bulk_operations.tiles import TileTreeOperation
from arches_querysets.models import (
    AliasedData,
    GraphWithPrefetching,
    ResourceTileTree,
    TileTree,
)

# Marker written to legacyid of every resource the seeders create, so the
# clear command can find and delete only seeded data.
SEED_LEGACYID_PREFIX = "dashboard-seed"


class ResourceBuilder:
    """Create graph resources through arches-querysets.

    Holds the shared save state (lifecycle state, save kwargs, graph cache) so
    one builder can create several resources. Its context managers are arches
    performance workarounds that cache or skip work arches otherwise repeats per
    tile; none changes the data written."""

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
        """arches performance workaround: skip the per-tile descriptor function.
        save() recomputes the descriptor once per resource anyway, so
        displaynames are unchanged."""
        pre_save = Tile._Tile__preSave
        post_save = Tile._Tile__postSave
        Tile._Tile__preSave = lambda *args, **kwargs: None
        Tile._Tile__postSave = lambda *args, **kwargs: None
        try:
            yield
        finally:
            Tile._Tile__preSave = pre_save
            Tile._Tile__postSave = post_save

    @contextmanager
    def cached_serialized_graphs(self):
        """arches performance workaround: hand every tile a cached serialized
        node list. A tile built mid-transaction can't resolve its own (its
        resourceinstance isn't committed), so arches falls back to
        Node.objects.get per node value -- hundreds of reads per permit. The list
        is a per-graph constant, so resolve it once per slug and share it (nodeids
        are unique, and readers only ever look up by id)."""
        builder = self
        merged = {"nodes": []}
        resolved = set()

        def refresh():
            for slug, graph in builder._graphs.items():
                if slug in resolved:
                    continue
                resolved.add(slug)
                published = graph.get_published_graph()
                if published and published.serialized_graph:
                    merged["nodes"].extend(published.serialized_graph["nodes"])

        orig = Tile.load_serialized_graph

        def patched(self):
            # A new graph slug may be seeded after the context opens.
            if len(resolved) != len(builder._graphs):
                refresh()
            self.serialized_graph = merged

        Tile.load_serialized_graph = patched
        try:
            yield
        finally:
            Tile.load_serialized_graph = orig

    @contextmanager
    def bypass_unique_constraints(self):
        """arches performance workaround: skip per-tile unique-constraint
        validation via arches' own setting. The seeders generate non-colliding
        data, so the per-tile CardModel/ConstraintModel queries only add cost.
        Set it on arches' system_settings (not django.conf) and restore after."""
        previous = arches_settings.BYPASS_UNIQUE_CONSTRAINT_TILE_VALIDATION
        arches_settings.BYPASS_UNIQUE_CONSTRAINT_TILE_VALIDATION = True
        try:
            yield
        finally:
            arches_settings.BYPASS_UNIQUE_CONSTRAINT_TILE_VALIDATION = previous

    @contextmanager
    def cached_resource_reviewer(self):
        """arches performance workaround: memoize the resource-reviewer group
        check. Every tile save walks user.groups.all() for the same admin user --
        an auth_group query per tile. Patch the shared permission framework (the
        singleton every caller delegates to) to memoize it by user id, so it costs
        one query for the run."""
        framework = _get_permission_framework()
        original = framework.user_is_resource_reviewer
        cache = {}

        def patched(user):
            key = getattr(user, "id", None)
            if key not in cache:
                cache[key] = original(user)
            return cache[key]

        framework.user_is_resource_reviewer = patched
        try:
            yield
        finally:
            framework.user_is_resource_reviewer = original

    @contextmanager
    def cached_edit_log_resource(self):
        """arches performance workaround: cache the per-resource reads in
        Tile.save_edit. It re-reads each tile's resource for the edit-log row (the
        graph_id FK plus a Resource.objects.get(...).displayname()), though every
        tile of a resource resolves the same row. Prime the FK and serve that
        lookup from a per-resource cache, then delegate to the real save_edit so
        the row written is unchanged."""
        original = Tile.save_edit
        resources = {}

        def patched(tile, *args, **kwargs):
            resource_id = tile.resourceinstance_id
            if resource_id not in resources:
                resources[resource_id] = Resource.objects.get(pk=resource_id)
            resource = resources[resource_id]
            tile.resourceinstance = resource
            manager_get = Resource.objects.get

            def cached_get(*get_args, **get_kwargs):
                if str(get_kwargs.get("resourceinstanceid")) == str(resource_id):
                    return resource
                return manager_get(*get_args, **get_kwargs)

            Resource.objects.get = cached_get
            try:
                return original(tile, *args, **kwargs)
            finally:
                Resource.objects.get = manager_get

        Tile.save_edit = patched
        try:
            yield
        finally:
            Tile.save_edit = original

    @contextmanager
    def skip_edit_log_overwrite_probe(self):
        """arches performance workaround: skip the blind-overwrite existence probe
        on each EditLog write. SaveSupportsBlindOverwriteMixin runs a SELECT per
        edit-log row to choose insert vs update; every edit log a seed run writes
        is new, so make add_force_keyword a no-op and let Django insert directly."""
        original = EditLog.add_force_keyword
        EditLog.add_force_keyword = lambda self, kwargs: kwargs
        try:
            yield
        finally:
            EditLog.add_force_keyword = original

    @contextmanager
    def cached_permitted_nodegroups(self):
        """arches performance workaround: memoize per-user nodegroup permission
        sets. Each tile save reads the admin user's viewable/editable/deletable
        nodegroups, and the user rebuilt per save recomputes them (a NodeGroup
        scan plus permission-cache lookups) every time. Memoize by user id and
        perms on the shared permission framework so they cost one pass per run."""
        framework = _get_permission_framework()
        original = framework.get_nodegroups_by_perm
        cache = {}

        def patched(user, perms, any_perm=True):
            key = (
                getattr(user, "id", None),
                tuple(perms) if isinstance(perms, (list, tuple)) else perms,
                any_perm,
            )
            if key not in cache:
                cache[key] = original(user, perms, any_perm=any_perm)
            return cache[key]

        framework.get_nodegroups_by_perm = patched
        try:
            yield
        finally:
            framework.get_nodegroups_by_perm = original

    @contextmanager
    def skip_tile_validation(self):
        """arches performance workaround: skip Django full_clean() on each new
        tile. arches validates every tile before insert, probing FK existence
        (node_groups) and tile-pk uniqueness (tiles) -- a SELECT or two per tile.
        The seeder builds tiles from the prefetched graph with fresh uuids and
        known-good FKs, so the persisted rows are identical without it."""
        original = TileTree.full_clean
        TileTree.full_clean = lambda self, *args, **kwargs: None
        try:
            yield
        finally:
            TileTree.full_clean = original

    @contextmanager
    def cached_grouping_nodes(self):
        """arches performance workaround: cache the grouping-node lookup per graph
        slug. Each save rebuilds it from scratch (a Node query with card/widget
        prefetches), though it's identical for every resource of a slug. Memoize
        it like the graph cache so each slug pays for it once per run."""
        original = TileTreeOperation._get_grouping_node_lookup
        cache = {}

        def patched(operation):
            slug = operation.graph.slug
            if slug not in cache:
                cache[slug] = original(operation)
            return cache[slug]

        TileTreeOperation._get_grouping_node_lookup = patched
        try:
            yield
        finally:
            TileTreeOperation._get_grouping_node_lookup = original

    @contextmanager
    def performance_workarounds(self):
        """Enter every arches performance workaround for a seed run. The command
        wraps the whole seed in this; tests build through it so the workarounds
        stay covered."""
        with (
            self.deferred_descriptors(),
            self.cached_serialized_graphs(),
            self.bypass_unique_constraints(),
            self.cached_resource_reviewer(),
            self.cached_edit_log_resource(),
            self.skip_edit_log_overwrite_probe(),
            self.cached_permitted_nodegroups(),
            self.skip_tile_validation(),
            self.cached_grouping_nodes(),
        ):
            yield

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
            legacyid=f"{SEED_LEGACYID_PREFIX}:{uuid.uuid4()}",
        )
        resource.aliased_data = AliasedData()
        # Reuse the prefetched graph instead of letting each append_tile/save
        # reload it; sealed=True tells arches-querysets it is already prefetched.
        resource.graph = graph
        resource.sealed = True
        if self.skip_refresh:
            resource.refresh_from_db = lambda *args, **kwargs: None
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
