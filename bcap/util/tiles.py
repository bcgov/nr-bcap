"""Read resource-instance references straight from raw tile data, without
hydrating an aliased tile tree."""

from collections import defaultdict

from arches.app.models.models import ResourceXResource, TileModel


def referenced_resource_ids(tiles, nodeid):
    """The resource ids referenced through a resource-instance node across the
    given tiles."""
    ids = set()
    for tile in tiles:
        for reference in tile.data.get(nodeid) or []:
            if reference.get("resourceId"):
                ids.add(reference["resourceId"])
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


def all_referenced_resource_ids(resourceinstance_id):
    """Every resource this one points at through a resource-instance node, from
    the resource_x_resource table Arches maintains on tile save (indexed, so no
    tile scan and no per-node knowledge needed)."""
    return {
        str(to_id)
        for to_id in ResourceXResource.objects.filter(
            from_resource_id=resourceinstance_id
        ).values_list("to_resource_id", flat=True)
    }
