"""Permit application save hook on the process_requirement nodegroup. A link to
a process-requirement template is swapped for a freshly cloned working copy in
save (before the resource-x-resource row is written), so a permit never points
at a shared template. The clone's descriptor embeds the permit, so it's
regenerated and indexed in post_save, once that link row exists."""

from arches.app.functions.base import BaseFunction
from arches.app.models.resource import Resource

from arches_querysets.models import ResourceTileTree

from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.util.aliases.bcap_service_request import BcapServiceRequestAliases
from bcap.util.aliases.process_requirement import ProcessRequirementAliases
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import get_node, node_id, nodes_for
from bcap.util.indexing import bulk_index

details = {
    "functionid": "60000000-0000-0000-0000-000000002010",
    "name": "Clone Process Requirement Templates",
    "type": "node",
    "modulename": "clone_process_requirement_templates.py",
    "description": (
        "On a permit application save, swaps a linked process-requirement "
        "template for a freshly cloned working copy."
    ),
    "defaultconfig": {"triggering_nodegroups": []},
    "classname": "CloneProcessRequirementTemplates",
    "component": "",
}


class CloneProcessRequirementTemplates(BaseFunction):
    def save(self, tile, request, context=None):
        node = get_node(
            GraphSlugs.BCAP_SERVICE_REQUEST,
            BcapServiceRequestAliases.PROCESS_REQUIREMENT,
        )
        service = ProcessRequirementService(request)
        tile._cloned_requirement_ids = []
        self._stamp_next_order(tile)
        for relationship in tile.data.get(str(node.pk)) or []:
            if self._is_template(relationship.get("resourceId")):
                clone = service.clone_by_id(relationship["resourceId"])
                relationship["resourceId"] = str(clone.pk)
                tile._cloned_requirement_ids.append(str(clone.pk))

    def post_save(self, tile, request, context=None):
        clone_ids = getattr(tile, "_cloned_requirement_ids", [])
        if not clone_ids:
            return
        # Permit descriptor must exist first -- a create+link save writes it
        # only after this hook -- so each clone descriptor can embed it.
        Resource.objects.get(pk=tile.resourceinstance_id).save_descriptors()
        clones = [Resource.objects.get(pk=clone_id) for clone_id in clone_ids]
        for clone in clones:
            clone.save_descriptors()
        bulk_index(clones)

    @staticmethod
    def _stamp_next_order(tile):
        """Set process_requirement_order on the tile to max existing order + 1.

        Skipped when the tile already exists in the database (a partial update
        such as a ministry-assignee change must not alter an order that is
        already stored) or when the order is already present in tile.data (the
        fixture builder sets explicit orders before the resource is first saved).
        """
        from arches.app.models.models import TileModel

        order_node = node_id(
            GraphSlugs.BCAP_SERVICE_REQUEST,
            BcapServiceRequestAliases.PROCESS_REQUIREMENT_ORDER,
        )
        if TileModel.objects.filter(pk=tile.tileid).exists():
            return
        if tile.data.get(order_node) is not None:
            return
        orders = [
            int(val)
            for t in TileModel.objects.filter(
                resourceinstance_id=tile.resourceinstance_id,
                nodegroup_id=tile.nodegroup_id,
            ).exclude(pk=tile.tileid)
            if (val := t.data.get(order_node)) is not None
        ]
        tile.data[order_node] = (max(orders) + 1) if orders else 0

    @staticmethod
    def _is_template(resource_id):
        # Only the template-flag node is needed to answer this, so skip
        # hydrating the rest of each requirement's tree.
        return (
            ResourceTileTree.get_tiles(
                GraphSlugs.PROCESS_REQUIREMENT,
                nodes=nodes_for(
                    GraphSlugs.PROCESS_REQUIREMENT,
                    [ProcessRequirementAliases.IS_TEMPLATE_REQUIREMENT],
                ),
            )
            .filter(pk=resource_id, is_template_requirement=True)
            .exists()
        )

    def get(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def on_import(self, *args, **kwargs):
        pass

    def after_function_save(self, *args, **kwargs):
        pass
