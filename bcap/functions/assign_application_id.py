"""Permit application save hook on the application_identification nodegroup.
Stamps a fresh sequence id on a permit's first save, overwriting any value an
out-of-box "clone permit template" copied in from the source; later edits keep
the id the permit already has."""

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.functions.base import BaseFunction
from arches.app.models.models import TileModel

from bcap.services.permit_application.permit_application_service import (
    PermitApplicationService,
)
from bcap.util.aliases.permit_application import PermitApplicationAliases
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import get_node

details = {
    "functionid": "60000000-0000-0000-0000-000000002011",
    "name": "Assign Application Id",
    "type": "node",
    "modulename": "assign_application_id.py",
    "description": (
        "On a permit application save, assigns a fresh sequence application id "
        "when it is missing or was copied from another resource."
    ),
    "defaultconfig": {"triggering_nodegroups": []},
    "classname": "AssignApplicationId",
    "component": "",
}


class AssignApplicationId(BaseFunction):
    def save(self, tile, request, context=None):
        # Only on the first save
        if TileModel.objects.filter(pk=tile.pk).exists():
            return
        node = get_node(
            GraphSlugs.PERMIT_APPLICATION, PermitApplicationAliases.APPLICATION_ID
        )
        datatype = DataTypeFactory().get_instance(node.datatype)
        tile.data[str(node.pk)] = datatype.transform_value_for_tile(
            PermitApplicationService.allocate_permit_application_id()
        )

    def get(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def on_import(self, *args, **kwargs):
        pass

    def after_function_save(self, *args, **kwargs):
        pass
