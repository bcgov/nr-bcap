from bcap.util.bcap_aliases import GraphSlugs, BCAPSiteSubmissionAliases as aliases
from bcgov_arches_common.util.bc_primary_descriptors_function import (
    BCPrimaryDescriptorsFunction,
)
from bcgov_arches_common.util.graph_lookup import GraphLookup

details = {
    "functionid": "60000000-0000-0000-0000-000000001005",
    "name": "BCAP Site Submission Descriptors",
    "type": "primarydescriptors",
    "modulename": "bcap_site_submission_descriptors.py",
    "description": "Function that provides the primary descriptors for BC Heritage Site Submissions",
    "defaultconfig": {
        "module": "arches_bcap.functions.bcap_site_submission_descriptors",
        "class_name": "BCAPSiteSubmissionDescriptors",
        "descriptor_types": {
            "name": {},
            "description": {},
            "map_popup": {},
        },
    },
    "classname": "BCAPSiteSubmissionDescriptors",
    "component": "views/components/functions/bcap-site-submission-descriptors",
}


class BCAPSiteSubmissionDescriptors(BCPrimaryDescriptorsFunction):
    # For Name part of descriptor
    _graph_slug = GraphSlugs.SITE_SUBMISSION
    _graph_lookup = None

    _name_nodes = [aliases.SUBMISSION_DATE, aliases.SUBMITTING_GOVERNMENT]
    _card_nodes = [
        aliases.SUBMITTED_SITE_COUNT,
        aliases.ASSIGNED_TO,
        aliases.COMPLETION_DATE,
    ]

    # Initializes the static nodes and datatypes data
    def __init__(self):
        super(BCPrimaryDescriptorsFunction).__init__()
        self._graph_lookup = GraphLookup(
            BCAPSiteSubmissionDescriptors._graph_slug,
            BCAPSiteSubmissionDescriptors._name_nodes
            + BCAPSiteSubmissionDescriptors._card_nodes,
        )

    def get_primary_descriptor_from_nodes(
        self, resource, config, context=None, descriptor=None
    ):
        return_value = ""

        try:
            if descriptor == "name":
                return self._get_site_submission_name(resource)

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

    def _get_site_submission_name(self, resource):
        submitted_date = self.get_value_from_node(
            self._graph_lookup.get_node(self._name_nodes[0]),
            self._graph_lookup.get_datatype(self._name_nodes[0]),
            resource,
        )

        submitting_government = self.get_value_from_node(
            self._graph_lookup.get_node(self._name_nodes[1]),
            self._graph_lookup.get_datatype(self._name_nodes[1]),
            resource,
        )

        return "%s > %s" % (submitted_date, submitting_government)
