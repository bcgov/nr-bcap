from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.descriptors import DescriptorTypes
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
    "description": "Function that provides the primary descriptors for BCAP Contributors",
    "defaultconfig": {
        "module": "bcap.functions.contributor_descriptors",
        "class_name": "ContributorDescriptors",
        "descriptor_types": {
            DescriptorTypes.NAME: {},
            DescriptorTypes.DESCRIPTION: {},
            DescriptorTypes.MAP_POPUP: {},
        },
        "triggering_nodegroups": [],
    },
    "classname": "ContributorDescriptors",
    "component": "views/components/functions/contributor-descriptors",
}


class ContributorDescriptorNodes:
    NAME = [aliases.CONTRIBUTOR_NAME, aliases.FIRST_NAME]
    CARD = [aliases.CONTRIBUTOR_TYPE, aliases.CONTRIBUTOR_ROLE]

    # A descriptor with no nodes renders as "".
    BY_DESCRIPTOR = {
        DescriptorTypes.NAME: NAME,
        DescriptorTypes.DESCRIPTION: CARD,
        DescriptorTypes.MAP_POPUP: [],
    }


class ContributorDescriptors(BCPrimaryDescriptorsFunction):
    # Arches builds a fresh instance per descriptor per resource, and a lookup
    # re-reads its nodes on first use, so share one for the whole process.
    _graph_lookup = GraphLookup(
        GraphSlugs.CONTRIBUTOR,
        ContributorDescriptorNodes.NAME + ContributorDescriptorNodes.CARD,
    )

    def get_primary_descriptor_from_nodes(
        self, resource, config, context=None, descriptor=None
    ):
        node_aliases = ContributorDescriptorNodes.BY_DESCRIPTOR.get(descriptor, [])
        values = [
            self.format_value(
                None,
                self.get_value_from_node(
                    self._graph_lookup.get_node(alias),
                    self._graph_lookup.get_datatype(alias),
                    resource,
                    context=context,
                ),
                show_name=False,
            )
            for alias in node_aliases
        ]

        return ", ".join(filter(None, values))
