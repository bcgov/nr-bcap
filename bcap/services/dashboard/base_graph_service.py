from arches.app.models.models import Node

from arches_querysets.models import ResourceTileTree, TileTree


class BaseGraphService:
    """Stateless helpers for reading representation-form node values."""

    # graph_slug -> {alias: (nodeid, nodegroup_id)}, filled once per process.
    _node_cache = {}

    @classmethod
    def _graph_nodes(cls, graph_slug):
        """Every node of a graph as {alias: (nodeid, nodegroup_id)}, fetched in a
        single query the first time and cached for the process (node ids are
        stable for the life of the graph)."""
        if graph_slug not in cls._node_cache:
            cls._node_cache[graph_slug] = {
                node["alias"]: (str(node["nodeid"]), str(node["nodegroup_id"]))
                for node in Node.objects.filter(
                    graph__slug=graph_slug, source_identifier=None
                ).values("alias", "nodeid", "nodegroup_id")
            }
        return cls._node_cache[graph_slug]

    @staticmethod
    def _nodes(graph_slug, aliases):
        """Node queryset for the given aliases, shaped to pass as the nodes
        argument to get_tiles."""
        return (
            Node.objects.filter(
                graph__slug=graph_slug,
                source_identifier=None,
                alias__in=aliases,
            )
            .exclude(datatype="semantic")
            .exclude(nodegroup=None)
            .select_related("nodegroup__parentnodegroup")
        )

    @classmethod
    def _node_info(cls, graph_slug, alias):
        """(nodeid, nodegroup_id) as strings for a graph's node alias."""
        return cls._graph_nodes(graph_slug)[alias]

    @classmethod
    def _node_id(cls, graph_slug, alias):
        """nodeid as a string for a graph's node alias."""
        return cls._node_info(graph_slug, alias)[0]

    @classmethod
    def _resources(cls, slug, ids, aliases):
        """Resources of the given graph for the given ids, with the requested
        aliases loaded as representation values."""
        return ResourceTileTree.get_tiles(
            slug,
            resource_ids=ids,
            nodes=cls._nodes(slug, aliases),
            as_representation=True,
        )

    @staticmethod
    def _nested_tiles(value):
        """The nodegroup tiles held by a node value (a single tile, a list of
        them, or none if the value is a plain leaf)."""
        items = value if isinstance(value, list) else [value]
        return [item for item in items if isinstance(item, TileTree)]

    @classmethod
    def _leaf_values(cls, aliased_data):
        """Yield an (alias, value) pair for every leaf value, descending into
        nested nodegroup tiles. The single traversal the id/value helpers
        filter."""
        if aliased_data is None:
            return
        # AliasedData is a SimpleNamespace; vars() reads its alias -> value dict.
        for key, value in vars(aliased_data).items():
            tiles = cls._nested_tiles(value)
            if not tiles:  # a leaf value, not a nodegroup
                yield key, value
            for tile in tiles:
                yield from cls._leaf_values(tile.aliased_data)

    @classmethod
    def _node_value(cls, aliased_data, alias):
        """First value under the given alias as a representation dict,
        descending into nested nodegroup tiles, or an empty dict if absent.
        Callers read keys defensively, so the empty case needs no fixed shape."""
        values = (
            value for key, value in cls._leaf_values(aliased_data) if key == alias
        )
        return next(values, {})

    @classmethod
    def _raw_value(cls, aliased_data, alias):
        """The stored node_value under the given alias (the raw value, not the
        formatted display_value), or None if unset."""
        return cls._node_value(aliased_data, alias).get("node_value")

    @staticmethod
    def _resource_ids(value):
        """Resource ids from a resource-instance(-list) representation value. An
        unset node represents as an empty list rather than a dict, so guard for
        that."""
        if not isinstance(value, dict):
            return []
        return [detail["resource_id"] for detail in value.get("details", [])]

    @classmethod
    def _resource_id(cls, value):
        """First resource id of a resource-instance representation value, or None."""
        ids = cls._resource_ids(value)
        return ids[0] if ids else None

    @classmethod
    def _referenced_ids_by_alias(cls, tiles, aliases):
        """Map each alias to the resource ids referenced under it across the
        given tiles, collecting every alias in a single traversal per tile."""
        aliases = set(aliases)
        result = {alias: set() for alias in aliases}
        for tile in tiles:
            for alias, value in cls._leaf_values(tile.aliased_data):
                if alias in aliases:
                    result[alias].update(cls._resource_ids(value))
        return result

    @classmethod
    def _referenced_ids(cls, tiles, alias):
        """All resource ids referenced under the given alias across the given
        tiles."""
        return cls._referenced_ids_by_alias(tiles, [alias])[alias]

    @staticmethod
    def _join_names(ids, names):
        """Comma-join the names looked up for the given ids."""
        return ", ".join(name for nid in ids if (name := names.get(nid, "")))
