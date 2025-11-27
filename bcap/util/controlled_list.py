from arches_controlled_lists.models import ListItem, ListItemValue


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
