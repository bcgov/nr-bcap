"""Utility for allocating reference numbers from the reference-number-widget
configuration stored in CardXNodeXWidget.config."""

from arches.app.models import models as arches_models
from bcgov_arches_common.services.reference_number import get_next_reference_number

from bcap.util.graph import get_node


def allocate_reference_number(graph_slug, node_alias):
    node = get_node(graph_slug, node_alias)
    card_widget = arches_models.CardXNodeXWidget.objects.filter(node=node).first()
    config = card_widget.config if card_widget is not None else {}
    abbreviation = config.get("prefix") if config is not None else None
    if not abbreviation:
        raise ValueError(
            f"prefix is not configured for node {node_alias!r} "
            f"on graph {graph_slug!r}"
        )
    sequence_digits = int(config.get("sequenceDigits") or 4)
    return get_next_reference_number(str(node.pk), abbreviation, sequence_digits)
