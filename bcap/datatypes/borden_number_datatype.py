import logging

from arches.app.datatypes.datatypes import NonLocalizedStringDataType
from arches.app.models import models
import re
from bcap.models.borden_number import BordenNumberCounter


borden_number_widget = models.Widget.objects.get(name="borden-number-widget")

details = {
    "datatype": "borden-number-datatype",
    "iconclass": "fa fa-file-code-o",
    "modulename": "borden_number_datatype.py",
    "classname": "BordenNumberDataType",
    "defaultwidget": borden_number_widget,
    "defaultconfig": None,
    "configcomponent": "views/components/datatypes/non-localized-string",
    "configname": "borden-number-datatype-config",
    "name": "Borden Number",
    "isgeometric": False,
    "issearchable": True,
}

logger = logging.getLogger(__name__)


class BordenNumberDataType(NonLocalizedStringDataType):
    def pre_tile_save(self, tile, nodeid):
        logger.debug("Tile: %s" % tile.data)
        value = tile.data[nodeid]
        borden_grid = re.sub("-.*", "", value)
        # print("Saving %s:%s" % (tile.resourceinstance_id, value))
        logger.debug(
            "Trying to reserve borden number %s for %s"
            % (value, tile.resourceinstance_id)
        )
        allocated_value = BordenNumberCounter.allocate_next_borden_number(borden_grid)
        if allocated_value != value:
            logger.debug(
                "Reserved borden number %s does not match %s -- setting value in tile"
                % (allocated_value, value)
            )
            tile.data[nodeid] = allocated_value
