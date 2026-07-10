import random

from arches_controlled_lists.models import ListItem, ListItemValue

from bcap.util.graph import get_node


def reference_value(slug, alias, label=None):
    """An item id from a node's controlled list: the one matching the given
    label, or the first item when no label is given."""
    list_id = get_node(slug, alias).config.get("controlledList")
    items = ListItem.objects.filter(list_id=list_id)
    if label is not None:
        item = items.filter(list_item_values__value=label).first()
    else:
        item = items.order_by("sortorder").first()
    if item is None:
        raise RuntimeError(
            f"Controlled list {list_id} backing {slug}.{alias} has no "
            f"{'matching ' if label else ''}items; load its reference data first."
        )
    return [str(item.pk)]


def random_reference_value(slug, alias):
    """A randomly chosen item id from the node's controlled list."""
    list_id = get_node(slug, alias).config.get("controlledList")
    item_ids = list(
        ListItem.objects.filter(list_id=list_id).values_list("pk", flat=True)
    )
    if not item_ids:
        raise RuntimeError(
            f"Controlled list {list_id} backing {slug}.{alias} has no items; "
            "load its reference data first."
        )
    return [str(random.choice(item_ids))]


def get_hierarchy_for_list_item(list_item_id):
    try:
        item = ListItem.objects.get(id=list_item_id)
        labels = []

        while item:
            label = (
                ListItemValue.objects.filter(
                    list_item=item,
                    valuetype_id="prefLabel",
                )
                .values_list("value", flat=True)
                .first()
            )

            if label:
                labels.append(label)

            item = item.parent

        labels.reverse()

        return labels
    except ListItem.DoesNotExist:
        return []
