"""Read resource-instance references straight from raw tile data, without
hydrating an aliased tile tree."""

from collections import defaultdict

from arches.app.models.models import TileModel


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
