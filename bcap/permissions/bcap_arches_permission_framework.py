"""BCAP graph permission policy, the framework that enforces it, and the applier
that writes it.

INTERNAL_GRAPH_PERMISSION_DEFAULTS is DATA-layer security: each graph maps to the
internal/staff groups that may touch it; anything not listed is denied by
default. settings.py installs this as PERMISSION_FRAMEWORK, so every arches path
that touches tiles runs through it. Route-level access for custom endpoints is
handled separately by DRF permission classes on the views.
"""

from typing import Iterable

from django.contrib.auth.models import User

from arches.app.models.models import Group, Node, NodeGroup
from arches.app.models.resource import Resource
from arches.app.permissions.arches_default_deny import (
    ArchesDefaultDenyPermissionFramework,
)
from arches.app.utils.permission_backend import (
    assign_perm,
    get_groups_with_perms,
    get_perms,
    remove_perm,
)

from bcap.permissions.groups import Groups

VIEW = ["view"]
READ_UPDATE = ["view", "change"]
EDIT = ["view", "change", "add"]
FULL = ["view", "change", "add", "delete"]

INTERNAL_GRAPH_PERMISSION_DEFAULTS = {
    "cef9c510-e3e6-4057-ac08-89ad926180b4": {  # archaeological_site (Inventory)
        Groups.ARCHAEOLOGY_BRANCH: FULL,
        Groups.INVENTORY_MANAGER: FULL,
        Groups.INVENTORY_REVIEWER: READ_UPDATE,
    },
    "52dd40f2-1dee-45d2-b72c-234c8cbb5418": {  # legislative_act
        Groups.ARCHAEOLOGY_BRANCH: FULL,
        Groups.RESOURCE_EDITOR: VIEW,
        Groups.RESOURCE_REVIEWER: VIEW,
        Groups.RESOURCE_EXPORTER: VIEW,
    },
    "aacf8bb6-3f6e-46d9-a551-b0749d7efffc": {  # local_government
        Groups.ARCHAEOLOGY_BRANCH: FULL,
        Groups.RESOURCE_EDITOR: VIEW,
        Groups.RESOURCE_REVIEWER: VIEW,
        Groups.RESOURCE_EXPORTER: VIEW,
    },
    # Admin-only graphs: Archaeology Branch only.
    "4e69d0a9-7af2-473f-929f-71d462ea32d1": {  # site_submission
        Groups.ARCHAEOLOGY_BRANCH: FULL,
    },
    "c3923080-d21e-42d7-b8f1-637b9d0ab63c": {  # project_sandbox (Sandcastle)
        Groups.ARCHAEOLOGY_BRANCH: FULL,
    },
    "19806d98-8200-45b4-9f5d-9f07d9a9aaa1": {  # hria_discontinued_data
        Groups.ARCHAEOLOGY_BRANCH: FULL,
    },
    "412444dd-b13f-4289-9f04-5c7f1878ad4e": {  # lg_person (Government Person)
        Groups.ARCHAEOLOGY_BRANCH: FULL,
    },
    # Permit graphs follow the access matrix. Submitter (external) is
    # owner-scoped in the view, so it is intentionally absent here.
    "5c900e2b-257c-4af3-b67f-b5caf3850f71": {  # permit_application
        Groups.ARCHAEOLOGY_BRANCH: FULL,
        Groups.RESOURCE_REVIEWER: READ_UPDATE,
        Groups.RESOURCE_EDITOR: EDIT,
        Groups.RESOURCE_EXPORTER: VIEW,
        Groups.PERMIT_REVIEWER: FULL,
        Groups.PERMIT_DECIDER: FULL,
        Groups.INVENTORY_REVIEWER: FULL,
        Groups.INVENTORY_MANAGER: FULL,
    },
    "0e74b1fa-1da4-4f17-9e65-dd79fbc96313": {  # process_requirement
        Groups.ARCHAEOLOGY_BRANCH: FULL,
        Groups.RESOURCE_REVIEWER: READ_UPDATE,
        Groups.RESOURCE_EDITOR: EDIT,
        Groups.RESOURCE_EXPORTER: VIEW,
        Groups.PERMIT_REVIEWER: READ_UPDATE,
        Groups.PERMIT_DECIDER: FULL,
        Groups.INVENTORY_REVIEWER: READ_UPDATE,
        Groups.INVENTORY_MANAGER: FULL,
    },
    "010b893e-c9d2-4dfe-b5d1-837c49c2bb9a": {  # requirement_submission
        Groups.ARCHAEOLOGY_BRANCH: FULL,
        Groups.RESOURCE_EDITOR: EDIT,
        Groups.RESOURCE_EXPORTER: VIEW,
    },
    "2da1c15f-1ab6-4122-9dbc-d10da693ac79": {  # site_visit (Inventory)
        Groups.ARCHAEOLOGY_BRANCH: FULL,
        Groups.INVENTORY_MANAGER: FULL,
        Groups.INVENTORY_REVIEWER: READ_UPDATE,
    },
    "f4b391f1-79d1-4886-ab2d-d72a197a9f21": {  # hca_permit (shared: Inv + Permit)
        Groups.ARCHAEOLOGY_BRANCH: FULL,
        Groups.INVENTORY_MANAGER: FULL,
        Groups.INVENTORY_REVIEWER: READ_UPDATE,
        Groups.PERMIT_DECIDER: FULL,
        Groups.PERMIT_REVIEWER: READ_UPDATE,
    },
    "605b0bbc-8661-4cf2-b340-df743a8c5f89": {  # contributor (shared: Inv + Permit)
        Groups.ARCHAEOLOGY_BRANCH: FULL,
        Groups.INVENTORY_MANAGER: FULL,
        Groups.INVENTORY_REVIEWER: READ_UPDATE,
        Groups.PERMIT_DECIDER: FULL,
        Groups.PERMIT_REVIEWER: READ_UPDATE,
    },
    "3caf329f-b8f7-11e6-84a5-026d961c88e6": {  # publication
        Groups.ARCHAEOLOGY_BRANCH: FULL,
        Groups.RESOURCE_REVIEWER: VIEW,
        Groups.RESOURCE_EDITOR: EDIT,
        Groups.RESOURCE_EXPORTER: VIEW,
    },
    "3e6a2880-14d4-11ec-9df0-5254008afee6": {  # repository
        Groups.ARCHAEOLOGY_BRANCH: FULL,
        Groups.RESOURCE_REVIEWER: VIEW,
        Groups.RESOURCE_EDITOR: EDIT,
        Groups.RESOURCE_EXPORTER: VIEW,
    },
}

VERB_TO_NODEGROUP_PERM = {
    "view": "read_nodegroup",
    "change": "write_nodegroup",
    "add": "write_nodegroup",
    "delete": "delete_nodegroup",
}
NO_ACCESS = "no_access_to_nodegroup"
# A group holding any of these model-level perms reads/writes EVERY nodegroup via
# arches' fallback unless denied at the object level (see _deny_groups).
MODEL_NODEGROUP_PERMS = {"read_nodegroup", "write_nodegroup", "delete_nodegroup"}

# The arches "anonymous" user is a Guest member
ANONYMOUS_USERNAME = "anonymous"

MANAGED_GROUPS = {
    name for policy in INTERNAL_GRAPH_PERMISSION_DEFAULTS.values() for name in policy
}


class BcapArchesPermissionFramework(ArchesDefaultDenyPermissionFramework):
    """Default-deny framework enforcing INTERNAL_GRAPH_PERMISSION_DEFAULTS."""

    @classmethod
    def _policy_group_ids(cls, graph_id, verb):
        """Group ids the policy grants the given verb on the given graph."""
        policy = INTERNAL_GRAPH_PERMISSION_DEFAULTS.get(graph_id, {})
        name_to_id = {group.name: group.id for group in Group.objects.all()}
        group_ids = []
        for name, verbs in policy.items():
            if verb in verbs and name in name_to_id:
                group_ids.append(name_to_id[name])
        return group_ids

    def get_index_values(
        self, resource: Resource, *, all_users: Iterable[User] = User.objects.none()
    ):
        """Permission metadata stamped onto the resource's Elasticsearch
        document so search results are filtered to what each user may see.
        Adds this graph's policy groups to the per-instance lists the base
        computes, since access here is granted by graph, not per instance."""
        permissions = super().get_index_values(resource, all_users=all_users)
        graph_id = str(resource.graph_id)
        index_field_verb = {"groups_read": "view", "groups_edit": "change"}

        # Union the graph-level policy into what the base computed from
        # per-instance perms, so search visibility matches the declared policy.
        for field, verb in index_field_verb.items():
            permissions[field] = list(
                set(permissions.get(field, []))
                | set(self._policy_group_ids(graph_id, verb))
            )
        return permissions

    @staticmethod
    def _graph_nodegroups(graph_id):
        """A published graph's nodegroups (a draft copy has a different id)."""
        nodegroup_ids = (
            Node.objects.filter(graph_id=graph_id, nodegroup_id__isnull=False)
            .values_list("nodegroup_id", flat=True)
            .distinct()
        )
        return list(NodeGroup.objects.filter(pk__in=nodegroup_ids))

    @staticmethod
    def _deny_groups(groups):
        """Managed groups (plus Guest) carrying model-level nodegroup perms, so
        they need an explicit no_access where not granted. Others are already
        denied by default-deny; denying them would only break multi-role users."""
        deny = set()
        for name in MANAGED_GROUPS | {Groups.GUEST}:
            group = groups.get(name)
            if group is None:
                continue
            codenames = {perm.codename for perm in group.permissions.all()}
            if codenames & MODEL_NODEGROUP_PERMS:
                deny.add(name)
        return deny

    @classmethod
    def _graph_assignments(cls, allow, groups, deny_groups, anonymous):
        """(principal, perm) pairs for one graph: grant allowed groups, deny the
        model-level-privileged ones that aren't granted."""
        assignments = []

        # Grant each allowed group its nodegroup perm, one per verb.
        for name, verbs in allow.items():
            if name not in groups:
                continue
            for verb in verbs:
                if verb in VERB_TO_NODEGROUP_PERM:
                    assignments.append((groups[name], VERB_TO_NODEGROUP_PERM[verb]))

        # Deny only model-privileged groups the graph does not grant; the rest
        # are denied by default-deny and would otherwise break multi-role users.
        for name in deny_groups - set(allow):
            assignments.append((groups[name], NO_ACCESS))

        # Anonymous mirrors Guest (which carries model-level read): denied unless
        # the graph grants Guest view.
        if anonymous and "view" not in allow.get(Groups.GUEST, []):
            assignments.append((anonymous, NO_ACCESS))
        return assignments

    @staticmethod
    def _clear_nodegroup_perms(nodegroup, anonymous):
        """Strip every group/anonymous perm off a nodegroup (owner access is implicit)."""
        for group, perms in get_groups_with_perms(nodegroup, attach_perms=True).items():
            for perm in perms:
                remove_perm(perm, group, nodegroup)
        if anonymous:
            for perm in get_perms(anonymous, nodegroup):
                remove_perm(perm, anonymous, nodegroup)

    @classmethod
    def apply_permission_defaults(cls, graph_ids=None):
        """Authoritatively re-assert the policy: clear group/anon perms per
        graph, then grant the defaults."""
        groups = {group.name: group for group in Group.objects.all()}
        anonymous = User.objects.filter(username=ANONYMOUS_USERNAME).first()
        if anonymous is None:
            raise RuntimeError(
                f"The {ANONYMOUS_USERNAME!r} user is missing; refusing to "
                "apply default-deny without denying the public."
            )
        deny_groups = cls._deny_groups(groups)
        applied = []
        for graph_id, allow in INTERNAL_GRAPH_PERMISSION_DEFAULTS.items():
            if graph_ids is not None and graph_id not in graph_ids:
                continue
            nodegroups = cls._graph_nodegroups(graph_id)
            if not nodegroups:
                continue

            assignments = cls._graph_assignments(allow, groups, deny_groups, anonymous)
            for nodegroup in nodegroups:
                cls._clear_nodegroup_perms(nodegroup, anonymous)
                for principal, perm in assignments:
                    assign_perm(perm, principal, nodegroup)
            applied.append(graph_id)
        return applied
