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
from bcap.util.aliases.permit_application import PermitApplicationAliases
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import get_node
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
            GraphSlugs.PERMIT_APPLICATION, PermitApplicationAliases.PROCESS_REQUIREMENT
        )
        service = ProcessRequirementService()
        tile._cloned_requirement_ids = []
        for relationship in tile.data.get(str(node.pk)) or []:
            if self._is_template(relationship.get("resourceId")):
                clone_id = str(service.clone_by_id(relationship["resourceId"]).pk)
                relationship["resourceId"] = clone_id
                tile._cloned_requirement_ids.append(clone_id)

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
    def _is_template(resource_id):
        return (
            ResourceTileTree.get_tiles(GraphSlugs.PROCESS_REQUIREMENT)
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
