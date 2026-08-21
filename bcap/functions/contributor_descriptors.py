from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.aliases.contributor import ContributorAliases as aliases
from bcgov_arches_common.util.bc_primary_descriptors_function import (
    BCPrimaryDescriptorsFunction,
)
from bcgov_arches_common.util.graph_lookup import GraphLookup

details = {
    "functionid": "60000000-0000-0000-0000-000000001007",
    "name": "Contributor Descriptors",
    "type": "primarydescriptors",
    "modulename": "contributor_descriptors.py",
    "description": "Function that provides the primary descriptors for BCAP Contributors resources",
    "defaultconfig": {
        "module": "bcap.functions.contributor_descriptors",
        "class_name": "ContributorDescriptors",
        "descriptor_types": {
            "name": {},
            "description": {},
            "map_popup": {},
        },
        "triggering_nodegroups": [],
    },
    "classname": "ContributorDescriptors",
    "component": "views/components/functions/contributor-descriptors",
}


class ContributorDescriptors(BCPrimaryDescriptorsFunction):
    # For Name part of descriptor
    _graph_slug = GraphSlugs.CONTRIBUTOR
    _graph_lookup = None

    _name_nodes = [aliases.CONTRIBUTOR_NAME, aliases.FIRST_NAME]
    _card_nodes = [aliases.CONTRIBUTOR_TYPE, aliases.CONTRIBUTOR_ROLE]

    def __init__(self):
        super(ContributorDescriptors).__init__()
        self._graph_lookup = GraphLookup(
            ContributorDescriptors._graph_slug,
            ContributorDescriptors._name_nodes + ContributorDescriptors._card_nodes,
        )

    def get_primary_descriptor_from_nodes(
        self, resource, config, context=None, descriptor=None
    ):
        return_value = ""

        try:
            if descriptor == "name":
                return self._get_name(resource)

            for node_alias in self._card_nodes:
                value = self.get_value_from_node(
                    self._graph_lookup.get_node(node_alias),
                    self._graph_lookup.get_datatype(node_alias),
                    resource,
                )
                if value:
                    return_value += self.format_value(
                        self._graph_lookup.get_node(node_alias).name, value, True
                    )

            return return_value

        except ValueError as e:
            print(e, "invalid nodegroupid participating in descriptor function.")

    def _get_name(self, resource):
        contributor_name = self.get_value_from_node(
            self._graph_lookup.get_node(aliases.CONTRIBUTOR_NAME),
            self._graph_lookup.get_datatype(aliases.CONTRIBUTOR_NAME),
            resource,
        )
        first_name = self.get_value_from_node(
            self._graph_lookup.get_node(aliases.FIRST_NAME),
            self._graph_lookup.get_datatype(aliases.FIRST_NAME),
            resource,
        )
        name = str(contributor_name) if contributor_name else ""
        if first_name:
            name = f"{name}, {first_name}"
        return name
