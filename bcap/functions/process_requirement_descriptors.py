from arches.app.models import models
from bcgov_arches_common.functions.abstract_primary_descriptors import (
    AbstractPrimaryDescriptors,
)
from bcap.util.aliases.permit_application import PermitApplicationAliases as pa
from bcap.util.aliases.process_requirement import ProcessRequirementAliases as aliases
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import node_id

details = {
    "functionid": "60000000-0000-0000-0000-000000001006",
    "name": "BCAP Process Requirement Descriptors",
    "type": "primarydescriptors",
    "modulename": "process_requirement_descriptors.py",
    "description": "Function that provides the primary descriptors for Process Requirements",
    "defaultconfig": {
        "module": "bcap.functions.process_requirement_descriptors",
        "class_name": "ProcessRequirementDescriptors",
        "descriptor_types": {
            "name": {
                "type": "name",
                "node_ids": [],
                "first_only": True,
                "show_name": False,
            },
            "description": {
                "type": "description",
                "node_ids": [],
                "first_only": False,
                "delimiter": "<br>",
                "show_name": True,
            },
            "map_popup": {
                "type": "map_popup",
                "node_ids": [],
                "first_only": False,
                "delimiter": "<br>",
                "show_name": True,
            },
        },
        "triggering_nodegroups": [],
    },
    "classname": "ProcessRequirementDescriptors",
    "component": "views/components/functions/process_requirement-descriptors",
}


class ProcessRequirementDescriptors(AbstractPrimaryDescriptors):
    _graph_slug = GraphSlugs.PROCESS_REQUIREMENT

    _empty_name_value = "(Unknown)"

    _name_node_aliases = [aliases.REQUIREMENT_NAME, aliases.IS_TEMPLATE_REQUIREMENT]
    # These don't have a geometry
    _popup_node_aliases = []
    _card_node_aliases = [
        aliases.REQUIREMENT_IDENTIFICATION,
        aliases.REQUIREMENT_STATUS,
        aliases.REQUIREMENT_PROCESS_START_DATE,
    ]

    def get_name_descriptor(self, resource, config, context):
        return self._get_process_requirement_name(
            resource, self._tiles_by_nodegroup(resource, self._name_node_aliases)
        )

    def _get_process_requirement_name(self, resource, tiles_by_nodegroup):
        name_datatype = self._datatypes[aliases.REQUIREMENT_NAME]
        display_value = ""

        def first_tile(alias):
            nodegroup_id = str(self._nodes[alias].nodegroup_id)
            return next(iter(tiles_by_nodegroup[nodegroup_id]), None)

        name_tile = first_tile(aliases.REQUIREMENT_NAME)
        is_template_tile = first_tile(aliases.IS_TEMPLATE_REQUIREMENT)

        if name_tile:
            display_value += "%s" % name_datatype.get_display_value(
                name_tile,
                self._nodes[aliases.REQUIREMENT_NAME],
            )

        if (
            is_template_tile
            and is_template_tile.data[
                str(self._nodes[aliases.IS_TEMPLATE_REQUIREMENT].nodeid)
            ]
        ):
            display_value += " (Template)"
        else:
            # The permit that references this requirement -- not a child that
            # references it as its grouping parent. A grouping parent has no
            # permit reference, so it shows just its name.
            permit = (
                models.ResourceXResource.objects.filter(
                    to_resource=resource,
                    from_resource__graph__slug=GraphSlugs.PERMIT_APPLICATION,
                )
                .select_related("from_resource")
                .first()
            )
            # Only an attached requirement has an app/module prefix; skip the
            # lookup entirely for a cloned or grouping-parent one (no permit).
            if permit is not None:
                descriptors = permit.from_resource.descriptors
                app_id = (descriptors or {}).get("en", {}).get("name")
                module_id = self._module_id_for_requirement(
                    resource.resourceinstanceid, permit.from_resource_id
                )
                # app id - module id - name, dropping whichever prefix is missing
                # so a grouping parent (no module) still reads cleanly.
                prefix = " - ".join(part for part in (app_id, module_id) if part)
                if prefix:
                    display_value = f"{prefix} - {display_value}"

        return display_value if display_value else self._empty_name_value

    @staticmethod
    def _module_id_for_requirement(requirement_id, permit_id):
        """The module id of the permit's process_module tile that lists this
        requirement (None for a grouping parent). Scoped to the permit's tiles by
        the indexed resourceinstance_id, not a whole-table JSONB scan."""
        reference_node = node_id(GraphSlugs.PERMIT_APPLICATION, pa.PROCESS_REQUIREMENT)
        module_id_node = node_id(GraphSlugs.PERMIT_APPLICATION, pa.MODULE_ID)
        child = (
            models.TileModel.objects.filter(
                resourceinstance_id=permit_id,
                data__contains={reference_node: [{"resourceId": str(requirement_id)}]},
            )
            .select_related("parenttile")
            .first()
        )
        parent = child.parenttile if child else None
        return parent.data.get(module_id_node) if parent else None
