"""Resource save hook that stamps a fresh sequence id on the first save of any
resource model that uses a reference-number-widget node.  The function is
graph-agnostic: it locates the reference-number-widget node for the saving
resource's graph at runtime, so the same function works for Permit Application,
BCAP Service Request, and any future graph that carries one such node."""

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.functions.base import BaseFunction
from arches.app.models import models as arches_models
from arches.app.models.models import TileModel

from bcgov_arches_common.services.reference_number import get_next_reference_number

_REFERENCE_NUMBER_WIDGET_ID = "10000000-0000-0000-0000-000000001006"

details = {
    "functionid": "60000000-0000-0000-0000-000000002011",
    "name": "Assign Application Id",
    "type": "node",
    "modulename": "assign_application_id.py",
    "description": (
        "On first save of a tile whose nodegroup contains a reference-number-widget "
        "node, assigns a fresh sequence id (overwriting any placeholder value). "
        "Works for any resource model with exactly one such node."
    ),
    "defaultconfig": {"triggering_nodegroups": []},
    "classname": "AssignApplicationId",
    "component": "",
}


class AssignApplicationId(BaseFunction):
    def save(self, tile, request, context=None):
        # Only on the first save of this tile.
        if TileModel.objects.filter(pk=tile.pk).exists():
            return

        # Find the reference-number-widget node for this graph.
        card_widget = (
            arches_models.CardXNodeXWidget.objects.filter(
                widget_id=_REFERENCE_NUMBER_WIDGET_ID,
                node__graph__slug=tile.resourceinstance.graph.slug,
                node__source_identifier=None,
            )
            .select_related("node")
            .first()
        )
        if card_widget is None:
            return

        node = card_widget.node

        # Only act when the reference-number node lives in this tile's nodegroup.
        if str(node.nodegroup_id) != str(tile.nodegroup_id):
            return

        config = card_widget.config or {}
        abbreviation = config.get("prefix")
        if not abbreviation:
            return

        sequence_digits = int(config.get("sequenceDigits") or 4)
        reference_number = get_next_reference_number(
            str(node.pk), abbreviation, sequence_digits
        )
        datatype = DataTypeFactory().get_instance(node.datatype)
        tile.data[str(node.pk)] = datatype.transform_value_for_tile(reference_number)

    def get(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def on_import(self, *args, **kwargs):
        pass

    def after_function_save(self, *args, **kwargs):
        pass
