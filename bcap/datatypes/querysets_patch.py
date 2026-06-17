"""arches_querysets never iterates touched tiles for the per-tile geojson
datatype, so its after_update_all is called with no tile and raises. Patch the
bulk operation to fan out per tile for that datatype, log-and-continue for
the rest. Installed from the app's ready() so it's set before any tile save."""

import logging

from django.db import OperationalError, ProgrammingError, connection

from arches_querysets.bulk_operations.tiles import TileTreeOperation
from arches_querysets.datatypes.geojson import GeojsonFeatureCollectionDataType

logger = logging.getLogger(__name__)


def after_update_all(self):
    touched_tiles = self.to_insert | self.to_update | self.to_delete
    for datatype in self.datatype_factory.datatype_instances.values():
        try:
            if isinstance(datatype, GeojsonFeatureCollectionDataType):
                for tile in touched_tiles:
                    datatype.after_update_all(tile=tile)
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
                "ALTER FUNCTION refresh_tile_geojson_geometries(uuid) "
                "SET jit = off"
            )
    except (ProgrammingError, OperationalError):
        pass


def temp_performance_fix_patch():
    TileTreeOperation.after_update_all = after_update_all
    disable_jit_on_tile_refresh()
