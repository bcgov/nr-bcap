"""Read resource-instance references straight from raw tile data, without
hydrating an aliased tile tree."""

from collections import defaultdict

from django.db.models import Q

from arches.app.models.models import ResourceXResource, TileModel

from bcap.util.aliased_data import AliasedDataReader
from bcap.util.bcap_aliases import ALIASED_DATA, RESOURCE_ID


def group_data(payload, group):
    """The aliased data of a group within a payload body, creating the path down
    to it. What callers write node values into."""
    return (
        payload.setdefault(ALIASED_DATA, {})
        .setdefault(group, {})
        .setdefault(ALIASED_DATA, {})
    )


def set_payload_node(payload, group, alias, node_value):
    """Write a node value into a payload group, creating the path."""
    group_data(payload, group)[alias] = {"node_value": node_value}


def payload_resource_id(payload, group, alias):
    """The resource id a payload's resource node points at, or None. Accepts a
    list or one bare reference, and a malformed body reads as absent."""
    node_value = AliasedDataReader._group_node_value(payload, group, alias)
    if isinstance(node_value, list):
        node_value = node_value[0] if node_value else {}
    return (node_value or {}).get(RESOURCE_ID)


def delete_tiles(tiles):
    """Delete one at a time through the proxy, so each deindexes and lands in the
    edit log. A queryset delete would do neither."""
    for tile in tiles:
        tile.delete()


def resource_instance_value(resource_id):
    """The value a resource-instance node holds: a one-element list, or an empty
    one when there is nothing to point at."""
    return [{RESOURCE_ID: str(resource_id)}] if resource_id else []


def resource_instance_id(node_value):
    """The id out of a resource-instance node value, or "" when it points at
    nothing. Reads the stored value, so a reference to a since-deleted resource
    still yields its id."""
    return node_value[0][RESOURCE_ID] if node_value else ""


def referenced_resource_ids(tiles, nodeid):
    """The resource ids referenced through a resource-instance node across the
    given tiles."""
    ids = set()
    for tile in tiles:
        for reference in tile.data.get(nodeid) or []:
            if reference.get(RESOURCE_ID):
                ids.add(reference[RESOURCE_ID])
    return ids


def references_by_source(source_ids, nodeid):
    """Map each source resource id to the resource ids it references through a
    resource-instance node."""
    grouped = defaultdict(set)
    tiles = TileModel.objects.filter(
        resourceinstance_id__in=list(source_ids), data__has_key=nodeid
    )
    for tile in tiles:
        grouped[str(tile.resourceinstance_id)].update(
            referenced_resource_ids([tile], nodeid)
        )
    return grouped


def all_referenced_resource_ids(*resourceinstance_ids):
    """Every resource these point at through a resource-instance node, from the
    resource_x_resource table Arches maintains on tile save (indexed, so no tile
    scan and no per-node knowledge needed)."""
    return {
        str(to_id)
        for to_id in ResourceXResource.objects.filter(
            from_resource_id__in=resourceinstance_ids
        ).values_list("to_resource_id", flat=True)
    }


def references_any(node, resource_ids):
    """Tiles whose resource-instance node points at any of these resources, by
    containment so the tiledata index is used. Matches nothing when empty."""
    references = [
        Q(**{f"data__{node}__contains": [{RESOURCE_ID: str(resource_id)}]})
        for resource_id in resource_ids
    ]
    return Q(*references, _connector=Q.OR) if references else Q(pk__in=[])
