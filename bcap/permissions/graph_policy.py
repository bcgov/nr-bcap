"""Which internal/staff groups may touch each graph.

Data-layer security: each graph slug maps to the groups granted verbs on its
nodegroups; anything not listed is denied. Search follows the same policy, but
only via what the framework stamps into the Elasticsearch document, so it lags
until a reindex. Routes are not covered here, arches' own or BCAP's: those gate
on groups through route_permissions.py. Nor are the dashboards, which are
authenticated-only and scoped by owner in their querysets.
"""

from bcap.permissions.groups import Groups, INTERNAL_GROUPS
from bcap.util.bcap_aliases import GraphSlugs

VIEW = ["view"]
EDIT = ["view", "change"]
EDIT_CREATE = ["view", "change", "add"]
FULL = ["view", "change", "add", "delete"]

# What a verb means to guardian, and which verb each permission field of the
# arches index document answers to.
VERB_TO_NODEGROUP_PERM = {
    "view": "read_nodegroup",
    "change": "write_nodegroup",
    "add": "write_nodegroup",
    "delete": "delete_nodegroup",
}
INDEX_FIELD_TO_VERB = {"groups_read": "view", "groups_edit": "change"}

NO_ACCESS = "no_access_to_nodegroup"
# Held at the model level, any of these reaches EVERY nodegroup unless an
# object-level denial says otherwise.
MODEL_NODEGROUP_PERMS = set(VERB_TO_NODEGROUP_PERM.values())

PERMIT_MATRIX = {
    Groups.ARCHAEOLOGY_BRANCH: FULL,
    Groups.RESOURCE_REVIEWER: EDIT,
    Groups.RESOURCE_EDITOR: EDIT_CREATE,
    Groups.RESOURCE_EXPORTER: VIEW,
    Groups.PERMIT_REVIEWER: FULL,
    Groups.PERMIT_DECIDER: FULL,
    Groups.PERMIT_SDM: FULL,
    Groups.INVENTORY_REVIEWER: FULL,
    Groups.INVENTORY_MANAGER: FULL,
}

INVENTORY_MATRIX = {
    Groups.ARCHAEOLOGY_BRANCH: FULL,
    Groups.INVENTORY_MANAGER: FULL,
    Groups.INVENTORY_REVIEWER: EDIT,
}

REFERENCE_MATRIX = {
    Groups.ARCHAEOLOGY_BRANCH: FULL,
    Groups.RESOURCE_EDITOR: VIEW,
    Groups.RESOURCE_REVIEWER: VIEW,
    Groups.RESOURCE_EXPORTER: VIEW,
}

ADMIN_ONLY = {Groups.ARCHAEOLOGY_BRANCH: FULL}

# Every role, external included. Ownership does the scoping: a draft belongs to
# whoever made it, and the queryset filters on that.
ALL_ROLES = {name: FULL for name in (Groups.SUBMITTER, *INTERNAL_GROUPS)}

INTERNAL_GRAPH_PERMISSION_DEFAULTS = {
    GraphSlugs.ARCHAEOLOGICAL_SITE: INVENTORY_MATRIX,
    GraphSlugs.SITE_VISIT: INVENTORY_MATRIX,
    GraphSlugs.LEGISLATIVE_ACT: REFERENCE_MATRIX,
    GraphSlugs.LOCAL_GOVERNMENT: REFERENCE_MATRIX,
    GraphSlugs.SITE_SUBMISSION: ADMIN_ONLY,
    GraphSlugs.PROJECT_SANDBOX: ADMIN_ONLY,  # Sandcastle
    GraphSlugs.HRIA_DISCONTINUED_DATA: ADMIN_ONLY,
    GraphSlugs.LG_PERSON: ADMIN_ONLY,  # Government Person
    GraphSlugs.WORKFLOW_DRAFTS: ALL_ROLES,
    # Permit graphs follow the access matrix. Submitter (external) is
    # owner-scoped in the view, so it is intentionally absent here.
    GraphSlugs.PERMIT_APPLICATION: PERMIT_MATRIX,
    GraphSlugs.ALTERATION: PERMIT_MATRIX,
    GraphSlugs.INSPECTION: PERMIT_MATRIX,
    GraphSlugs.INVESTIGATION: PERMIT_MATRIX,
    GraphSlugs.INFORMATION_REQUEST: PERMIT_MATRIX,
    GraphSlugs.NOTICE_OF_PROJECT_INTENT: PERMIT_MATRIX,
    GraphSlugs.BCAP_MESSAGE: PERMIT_MATRIX,
    GraphSlugs.PROCESS_REQUIREMENT: {
        Groups.ARCHAEOLOGY_BRANCH: FULL,
        Groups.RESOURCE_REVIEWER: EDIT,
        Groups.RESOURCE_EDITOR: EDIT_CREATE,
        Groups.RESOURCE_EXPORTER: VIEW,
        Groups.PERMIT_REVIEWER: EDIT,
        Groups.PERMIT_DECIDER: FULL,
        Groups.PERMIT_SDM: FULL,
        Groups.INVENTORY_REVIEWER: EDIT,
        Groups.INVENTORY_MANAGER: FULL,
    },
    GraphSlugs.DOCUMENT_SUBMISSION: {
        Groups.ARCHAEOLOGY_BRANCH: FULL,
        Groups.RESOURCE_EDITOR: EDIT_CREATE,
        Groups.RESOURCE_EXPORTER: VIEW,
    },
    # Shared: Inventory + Permit.
    GraphSlugs.HCA_PERMIT: {
        **INVENTORY_MATRIX,
        Groups.PERMIT_DECIDER: FULL,
        Groups.PERMIT_SDM: FULL,
        Groups.PERMIT_REVIEWER: EDIT,
    },
    GraphSlugs.CONTRIBUTOR: {
        **INVENTORY_MATRIX,
        Groups.PERMIT_DECIDER: FULL,
        Groups.PERMIT_SDM: FULL,
        Groups.PERMIT_REVIEWER: EDIT,
    },
    GraphSlugs.PUBLICATION: {
        Groups.ARCHAEOLOGY_BRANCH: FULL,
        Groups.RESOURCE_REVIEWER: VIEW,
        Groups.RESOURCE_EDITOR: EDIT_CREATE,
        Groups.RESOURCE_EXPORTER: VIEW,
    },
    GraphSlugs.REPOSITORY: {
        Groups.ARCHAEOLOGY_BRANCH: FULL,
        Groups.RESOURCE_REVIEWER: VIEW,
        Groups.RESOURCE_EDITOR: EDIT_CREATE,
        Groups.RESOURCE_EXPORTER: VIEW,
    },
}

MANAGED_GROUPS = {
    name for policy in INTERNAL_GRAPH_PERMISSION_DEFAULTS.values() for name in policy
}


def policy_slugs(slugs=None):
    """The graphs the policy covers, narrowed to the requested slugs. Unknown
    slugs are dropped, since callers other than the command that validates them
    exist."""
    if slugs is None:
        return list(INTERNAL_GRAPH_PERMISSION_DEFAULTS)
    return [slug for slug in slugs if slug in INTERNAL_GRAPH_PERMISSION_DEFAULTS]


def nodegroup_perms(slug):
    """Group name to the guardian nodegroup perms a graph grants it. A graph the
    policy omits grants nothing."""
    return {
        name: {VERB_TO_NODEGROUP_PERM[verb] for verb in verbs}
        for name, verbs in INTERNAL_GRAPH_PERMISSION_DEFAULTS.get(slug, {}).items()
    }


def index_group_names(slug):
    """Index permission field to the group names a graph lists in it."""
    allow = INTERNAL_GRAPH_PERMISSION_DEFAULTS.get(slug, {})
    return {
        field: [name for name, verbs in allow.items() if verb in verbs]
        for field, verb in INDEX_FIELD_TO_VERB.items()
    }
