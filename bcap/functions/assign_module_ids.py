"""Permit application save hook on the process_module nodegroup.

Fills the Module -> Requirement id hierarchy however a module reaches a permit. In
save (before the tile is written) it mints the module's unique id when it is
missing: the module type and a database-wide sequence value (e.g.
INVESTIGATION-48213). In post_save (once every tile in the save is written) it
stamps each of the module's process requirements with an id derived from that
module id, the requirement name, and its order, so shared names still resolve to
distinct ids (e.g. INVESTIGATION-48213-SITE-ASSESSMENT-001)."""

import re

from django.db import connection

from arches.app.functions.base import BaseFunction
from arches.app.models.models import TileModel

from bcap.util.aliases.permit_application import PermitApplicationAliases as pa
from bcap.util.aliases.process_requirement import ProcessRequirementAliases as prq
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import node_id
from bcap.util.i18n import localized, localized_string
from bcap.util.tiles import referenced_resource_ids

details = {
    "functionid": "60000000-0000-0000-0000-000000002012",
    "name": "Assign Module Ids",
    "type": "node",
    "modulename": "assign_module_ids.py",
    "description": (
        "On a permit application save, mints a module's unique id when missing "
        "and stamps its process requirements with ids derived from it."
    ),
    "defaultconfig": {"triggering_nodegroups": []},
    "classname": "AssignModuleIds",
    "component": "",
}


class AssignModuleIds(BaseFunction):
    def save(self, tile, request, context=None):
        """Mint the module id; post_save reads it back to stamp the
        requirements."""
        module_id_node = node_id(GraphSlugs.PERMIT_APPLICATION, pa.MODULE_ID)
        tile._minted_module_id = None
        if tile.data.get(module_id_node):
            return
        name_node = node_id(GraphSlugs.PERMIT_APPLICATION, pa.MODULE_NAME)
        module_type = self._slug(localized_string(tile.data.get(name_node)))
        module_id = f"{module_type}-{self._next_sequence()}"
        tile.data[module_id_node] = module_id
        tile._minted_module_id = module_id

    def post_save(self, tile, request, context=None):
        """In post_save, not save: the child tiles are only written by now, and
        they save in pk order, not parent-first."""
        module_id = getattr(tile, "_minted_module_id", None)
        if not module_id:
            return
        order_node = node_id(
            GraphSlugs.PERMIT_APPLICATION, pa.PROCESS_REQUIREMENT_ORDER
        )
        reference_node = node_id(GraphSlugs.PERMIT_APPLICATION, pa.PROCESS_REQUIREMENT)
        for child in TileModel.objects.filter(parenttile_id=tile.pk):
            order = int(child.data.get(order_node) or 0)
            for requirement_id in referenced_resource_ids([child], reference_node):
                self._stamp_requirement(requirement_id, module_id, order)

    def _stamp_requirement(self, requirement_id, module_id, order):
        """Write the id straight to the identification tile rather than through a
        ResourceTileTree save: post_save already runs inside the permit's durable
        atomic block, and a nested one is disallowed."""
        if not requirement_id:
            return
        name_node = node_id(GraphSlugs.PROCESS_REQUIREMENT, prq.REQUIREMENT_NAME)
        identification_node = node_id(
            GraphSlugs.PROCESS_REQUIREMENT, prq.REQUIREMENT_IDENTIFICATION
        )
        tile = TileModel.objects.filter(
            resourceinstance_id=requirement_id, data__has_key=identification_node
        ).first()
        if not tile:
            return
        name = self._slug(localized_string(tile.data.get(name_node)))
        tile.data[identification_node] = localized(f"{module_id}-{name}-{order:03d}")
        tile.save(update_fields=["data"])

    @staticmethod
    def _next_sequence():
        with connection.cursor() as cursor:
            cursor.execute("SELECT nextval('bcap_process_module_id_seq')")
            return cursor.fetchone()[0]

    @staticmethod
    def _slug(text):
        return re.sub(r"[^A-Z0-9]+", "-", (text or "").upper()).strip("-")

    def get(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def on_import(self, *args, **kwargs):
        pass

    def after_function_save(self, *args, **kwargs):
        pass
