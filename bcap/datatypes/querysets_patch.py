"""arches_querysets never iterates touched tiles for the per-tile geojson
datatype, so its after_update_all is called with no tile and raises. Patch the
bulk operation to fan out per tile for that datatype, log-and-continue for
the rest. Installed from the app's ready() so it's set before any tile save."""

import logging

from django.db import OperationalError, ProgrammingError, connection
from django.db.models import Exists, OuterRef

from arches.app.models.models import Node, TileModel

from arches_querysets.bulk_operations.tiles import TileTreeOperation
from arches_querysets.datatypes.geojson import GeojsonFeatureCollectionDataType

logger = logging.getLogger(__name__)


def geojson_after_update_all(self, tile=None):
    """arches_querysets' geojson after_update_all dereferences the tile, but
    arches' import_business_data (package load) calls after_update_all() with no
    tile -- crashing the import. Defer to the base datatype's global hook in that
    case; keep the per-resource fan-out when a tile is given."""
    if tile is None:
        return super(GeojsonFeatureCollectionDataType, self).after_update_all()
    nodes_exist_subquery = Node.objects.filter(
        nodegroup_id=OuterRef("nodegroup_id"),
        datatype="geojson-feature-collection",
    )
    tiles = TileModel.objects.filter(resourceinstance=tile.resourceinstance_id).filter(
        Exists(nodes_exist_subquery)
    )
    for resource_tile in tiles:
        super(GeojsonFeatureCollectionDataType, self).after_update_all(resource_tile)


def after_update_all(self):
    changed = self.to_insert | self.to_update | self.to_delete
    for datatype in self.datatype_factory.datatype_instances.values():
        try:
            if isinstance(datatype, GeojsonFeatureCollectionDataType):
                if changed:
                    datatype.after_update_all(tile=next(iter(changed)))
            else:
                datatype.after_update_all()
        except Exception:
            # A failure here can leave the DB unusable, so the upstream
            # contract is to log and continue as the last step under a
            # durable transaction.
            logger.error(
                f"Error in {datatype.__class__.__name__}.after_update_all():",
                exc_info=True,
            )
            continue


def disable_jit_on_tile_refresh():
    """Pin jit=off on the per-tile geojson refresh. It's a sub-ms point write
    run once per tile, so JIT's per-call LLVM compile is pure overhead (~1.7x
    slower seeding, measured). Re-asserted here in case an arches_querysets
    upgrade recreates the function without the setting. No-op when the function
    isn't there yet (eg a fresh DB mid-migrate) or the DB is unreachable."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER FUNCTION refresh_tile_geojson_geometries(uuid) " "SET jit = off"
            )
    except (ProgrammingError, OperationalError):
        pass


def temp_performance_fix_patch():
    TileTreeOperation.after_update_all = after_update_all
    GeojsonFeatureCollectionDataType.after_update_all = geojson_after_update_all
    disable_jit_on_tile_refresh()
