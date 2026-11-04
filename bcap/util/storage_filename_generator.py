import logging
import os
from arches.app.models import models
from arches.app import datatypes

logger = logging.getLogger(__name__)

borden_number_node = None
datatype_factory = None
borden_number_datatype = None


def generate_filename(instance, filename):
    logger.debug("Instance: %s (%s)", instance, type(instance))
    logger.debug("File ID: %s (%s)", instance.fileid, type(instance.fileid))
    logger.debug("Tile: %s (%s)", instance.tile, type(instance.tile))
    logger.debug(
        "ResourceInstance: %s (%s)",
        instance.tile.resourceinstance,
        type(instance.tile.resourceinstance),
    )
    logger.debug(
        "GraphID: %s (%s)",
        instance.tile.resourceinstance.graph.graphid,
        type(instance.tile.resourceinstance.graph.graphid),
    )
    logger.debug(
        "Graph Slug: %s (%s)",
        instance.tile.resourceinstance.graph.slug,
        type(instance.tile.resourceinstance.graph.graphid),
    )
    if not hasattr(generate_filename, "borden_number_node"):
        generate_filename.borden_number_node = models.Node.objects.filter(
            alias="borden_number"
        ).first()
        logger.debug(
            "Got borden number node: %s", str(generate_filename.borden_number_node)
        )

    if not hasattr(generate_filename, "borden_number_datatype"):
        generate_filename.borden_number_datatype = (
            datatypes.datatypes.DataTypeFactory().get_instance(
                generate_filename.borden_number_node.datatype
            )
        )
        logger.debug(
            "Got borden number datatype: %s",
            str(generate_filename.borden_number_datatype),
        )

    borden_number_tile = models.TileModel.objects.filter(
        resourceinstance=instance.tile.resourceinstance,
        nodegroup=generate_filename.borden_number_node.nodegroup,
    ).first()
    logger.debug("Got borden number tile: %s", str(borden_number_tile))
    borden_number = None

    paths = []
    if borden_number_tile:
        borden_number = generate_filename.borden_number_datatype.get_display_value(
            borden_number_tile, generate_filename.borden_number_node
        )
        paths = (
            borden_number.split("-")
            if borden_number and "-" in borden_number
            else [str(instance.tile.resourceinstance.resourceinstanceid)]
        )
    else:
        paths.append(str(instance.tile.resourceinstance.resourceinstanceid))

    graph_slug = (
        instance.tile.resourceinstance.graph.slug
        if instance.tile.resourceinstance.graph.slug
        else "system_settings"
    )
    logger.debug("Paths: %s", str(paths))
    root, ext = os.path.splitext(filename)
    path = os.path.join(
        graph_slug,
        *paths,
        f"{root}-{instance.tile.tileid}{ext}",
    )
    logger.debug("Generated filepath: %s", path)
    return path
