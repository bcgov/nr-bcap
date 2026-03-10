import logging

from arches.app.models import models
from arches_controlled_lists.models import ListItem, ListItemValue

from bcap.util.graph import get_current_graph

logger = logging.getLogger(__name__)

ARCHAEOLOGICAL_SITE_SLUG = "archaeological_site"
LEGISLATIVE_ACT_SLUG = "legislative_act"


def _extract_list_item_id(reference_value) -> str | None:
    if not reference_value:
        return None

    if isinstance(reference_value, list) and len(reference_value) > 0:
        item = reference_value[0]

        if isinstance(item, dict):
            labels = item.get("labels", [])

            if labels and isinstance(labels, list) and len(labels) > 0:
                list_item_id = labels[0].get("list_item_id")

                if list_item_id:
                    return list_item_id

            uri = item.get("uri", "")

            if uri:
                parts = uri.rstrip("/").split("/")
                return parts[-1] if parts else None

        if isinstance(item, str):
            return item

    if isinstance(reference_value, str):
        return reference_value

    return None


def _extract_resource_instance_id(resource_instance_value) -> list[str]:
    if not resource_instance_value:
        return []

    if isinstance(resource_instance_value, list):
        return [
            ref.get("resourceId")
            for ref in resource_instance_value
            if isinstance(ref, dict) and ref.get("resourceId")
        ]

    return []


def _get_node(graph_slug: str, alias: str) -> models.Node:
    graph = get_current_graph(graph_slug)
    return models.Node.objects.get(alias=alias, graph=graph)


def _resolve_hierarchy(list_item_id: str) -> dict:
    labels = []
    item = ListItem.objects.filter(id=list_item_id).first()

    while item:
        label = (
            ListItemValue.objects.filter(list_item=item, valuetype_id="prefLabel")
            .values_list("value", flat=True)
            .first()
        )

        if label:
            labels.append(label)

        item = item.parent

    labels.reverse()

    return {
        "class_name": labels[0] if len(labels) > 0 else None,
        "type_name": labels[1] if len(labels) > 1 else None,
        "subtype": labels[2] if len(labels) > 2 else None,
        "descriptor": labels[3] if len(labels) > 3 else None,
    }


def calculate_register_types(
    typology_rows: list[dict],
    act_sections: list[str],
) -> list[str]:
    register_types = set()

    all_classes = {r["class_name"] for r in typology_rows if r["class_name"]}
    all_types = {r["type_name"] for r in typology_rows if r["type_name"]}
    all_subtypes = {r["subtype"] for r in typology_rows if r["subtype"]}
    all_descriptors = {r["descriptor"] for r in typology_rows if r["descriptor"]}

    # 1. Archaeological Site
    if (
        "Precontact" in all_classes
        or "Ancestral Remains" in all_types
        or "Human Remains" in all_types
        or "Culturally Modified Tree" in all_types
        or "Rock Art" in all_subtypes
        or "Airplane Wreck" in all_descriptors
        or "Shipwreck" in all_descriptors
    ):
        register_types.add("Archaeological Site")

    # 2. Ancestral Remains
    if "Ancestral Remains" in all_types or "Human Remains" in all_types:
        register_types.add("Ancestral Remains")

    # 3. Rock Art
    if "Rock Art" in all_subtypes:
        register_types.add("Rock Art")

    # 4. Heritage Wreck
    if "Airplane Wreck" in all_descriptors or "Shipwreck" in all_descriptors:
        register_types.add("Heritage Wreck")

    # 5. S.4 Agreement with First Nations
    if "S. 4" in act_sections:
        register_types.add("S.4 Agreement with First Nations")

    # 6. Palaeontological Site
    if "Palaeontological" in all_classes:
        register_types.add("Palaeontological Site")

    # 7. Provincial Heritage Site or Object
    if "S. 9" in act_sections or "S. 11.1" in act_sections:
        register_types.add("Provincial Heritage Site or Object")

    # 8. Non-Designated Historic Site
    if "Postcontact" in all_classes:
        excluded_classes = {"Precontact", "Traditional Use"}
        excluded_types = {"Ancestral Remains", "Human Remains"}
        excluded_descriptors = {"Airplane Wreck", "Shipwreck"}

        if (
            not all_classes & excluded_classes
            and not all_types & excluded_types
            and not all_descriptors & excluded_descriptors
        ):
            register_types.add("Non-Designated Historic Site")

    return sorted(register_types)


class RegisterTypeApi:
    _la_act_section_node = None
    _legislative_act_node = None
    _register_type_list_id = None
    _typology_class_node = None

    def _build_reference_value(self, list_item_ids: list[str]) -> list[dict]:
        values = []
        for item_id in list_item_ids:
            item = ListItem.objects.filter(id=item_id).first()

            if not item:
                continue

            values.append(
                {
                    "uri": str(item.uri),
                    "labels": [
                        {
                            "id": str(lv.id),
                            "value": lv.value,
                            "language_id": lv.language_id,
                            "list_item_id": str(item_id),
                            "valuetype_id": lv.valuetype_id,
                        }
                        for lv in ListItemValue.objects.filter(list_item=item)
                    ],
                    "list_id": str(item.list_id),
                }
            )

        return values

    def _build_register_type_map(self) -> dict[str, str]:
        return dict(
            ListItemValue.objects.filter(
                list_item__list_id=self._register_type_list_id,
                valuetype_id="prefLabel",
            ).values_list("value", "list_item_id")
        )

    def _get_act_sections(self, resourceinstanceid: str) -> list[str]:
        authority_tiles = models.TileModel.objects.filter(
            resourceinstance_id=resourceinstanceid,
            nodegroup_id=self._legislative_act_node.nodegroup_id,
        )

        la_nodeid = str(self._legislative_act_node.nodeid)
        act_section_nodeid = str(self._la_act_section_node.nodeid)
        act_sections = []

        for tile in authority_tiles:
            la_refs = _extract_resource_instance_id(tile.data.get(la_nodeid))

            for la_resource_id in la_refs:
                la_tiles = models.TileModel.objects.filter(
                    resourceinstance_id=la_resource_id,
                    nodegroup_id=self._la_act_section_node.nodegroup_id,
                )

                for la_tile in la_tiles:
                    act_section_data = la_tile.data.get(act_section_nodeid)
                    if not act_section_data:
                        continue

                    if isinstance(act_section_data, dict):
                        value = act_section_data.get("en", {}).get("value", "")
                    elif isinstance(act_section_data, str):
                        value = act_section_data
                    else:
                        continue

                    if value:
                        act_sections.append(value.strip())

        return act_sections

    def _get_typology_rows(self, resourceinstanceid: str) -> list[dict]:
        tiles = models.TileModel.objects.filter(
            resourceinstance_id=resourceinstanceid,
            nodegroup_id=self._typology_class_node.nodegroup_id,
        )

        nodeid = str(self._typology_class_node.nodeid)
        rows = []

        for tile in tiles:
            reference_value = tile.data.get(nodeid)
            list_item_id = _extract_list_item_id(reference_value)

            if not list_item_id:
                continue

            hierarchy = _resolve_hierarchy(list_item_id)
            rows.append(hierarchy)

        return rows

    def _initialize(self):
        if not self._typology_class_node:
            self._typology_class_node = _get_node(
                ARCHAEOLOGICAL_SITE_SLUG, "typology_class"
            )
            self._legislative_act_node = _get_node(
                ARCHAEOLOGICAL_SITE_SLUG, "legislative_act"
            )
            self._la_act_section_node = _get_node(LEGISLATIVE_ACT_SLUG, "act_section")
            self._register_type_list_id = _get_node(
                ARCHAEOLOGICAL_SITE_SLUG, "register_type"
            ).config.get("controlledList")

    def calculate(self, resourceinstanceid: str) -> dict:
        self._initialize()

        typology_rows = self._get_typology_rows(resourceinstanceid)
        act_sections = self._get_act_sections(resourceinstanceid)

        labels = calculate_register_types(typology_rows, act_sections)

        register_type_map = self._build_register_type_map()
        matched_uuids = []
        missing_labels = []

        for label in labels:
            uuid = register_type_map.get(label)
            if uuid:
                matched_uuids.append(str(uuid))
            else:
                missing_labels.append(label)

        if missing_labels:
            logger.warning(
                "Register Type labels not found in controlled list: %s",
                missing_labels,
            )

        reference_value = self._build_reference_value(matched_uuids)

        return {
            "status": "success",
            "register_types": labels,
            "register_type_ids": matched_uuids,
            "reference_value": reference_value,
            "missing_labels": missing_labels,
        }
