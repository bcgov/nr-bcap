"""Default-deny framework enforcing the policy in graph_policy.py, and the
applier that writes it to Guardian. Installed as PERMISSION_FRAMEWORK, so every
arches path touching tiles runs through it. Route access is separate: DRF
permission classes on the views.
"""

from django.contrib.contenttypes.models import ContentType
from django.core.cache import caches
from django.db import transaction
from guardian.models import GroupObjectPermission, UserObjectPermission

from arches.app.models.models import GraphModel, Group, NodeGroup
from arches.app.permissions.arches_default_deny import (
    ArchesDefaultDenyPermissionFramework,
)
from arches.app.utils.permission_backend import assign_perm

from bcap.permissions.graph_policy import (
    MANAGED_GROUPS,
    MODEL_NODEGROUP_PERMS,
    NO_ACCESS,
    index_group_names,
    nodegroup_perms,
    policy_slugs,
)
from bcap.permissions.groups import Groups

ANONYMOUS_USERNAME = "anonymous"


class BcapArchesPermissionFramework(ArchesDefaultDenyPermissionFramework):
    def user_is_resource_reviewer(self, user):
        """Signed-in users author for real; the public user keeps the stock
        check. A non-reviewer's tile save lands in provisionaledits with the
        tile written empty, and BCAP has no approval step."""
        if user.is_authenticated and user.username != ANONYMOUS_USERNAME:
            return True
        return super().user_is_resource_reviewer(user)

    def get_index_values(self, resource, **kwargs):
        """Permission metadata for the index document. Access here is granted
        by graph, so the policy unions into the base's per-instance lists."""
        permissions = super().get_index_values(resource, **kwargs)
        for field, names in index_group_names(resource.graph.slug).items():
            granted = Group.objects.filter(name__in=names).values_list("id", flat=True)
            permissions[field] = list(set(permissions[field]) | set(granted))
        return permissions

    @classmethod
    @transaction.atomic
    def apply_permission_defaults(cls, slugs=None):
        """Clear group and user perms per graph, then grant the policy; returns
        the graph ids touched. Atomic: clearing without re-granting locks
        everyone out."""
        graph_id_by_slug = cls._published_graph_ids()
        groups_by_name = {group.name: group for group in Group.objects.all()}
        deny_groups = cls._groups_needing_denial()

        applied = []
        for slug in policy_slugs(slugs):
            graph_id = graph_id_by_slug.get(slug)
            nodegroups = NodeGroup.objects.filter(node__graph_id=graph_id).distinct()
            if not nodegroups:
                continue

            cls._clear_nodegroup_perms(nodegroups)
            for perm, group in cls._assignments(slug, groups_by_name, deny_groups):
                assign_perm(perm, group, nodegroups)
            applied.append(graph_id)

        caches["user_permission"].clear()
        return applied

    @staticmethod
    def _published_graph_ids():
        """Graph id by slug, published graphs only: a draft copy keeps its
        source's slug."""
        return dict(
            GraphModel.objects.filter(
                slug__isnull=False, source_identifier__isnull=True
            ).values_list("slug", "graphid")
        )

    @staticmethod
    def _groups_needing_denial():
        """The groups an explicit denial has to name. With no object-level row
        arches falls back to model-level perms (arches_permission_base.py:673),
        so a group holding those reads every nodegroup the policy skips. Denying
        wider backfires: a denial beats the grants a multi-role user's other
        groups carry. Guest is here for the public user."""
        return set(
            Group.objects.filter(
                name__in=MANAGED_GROUPS | {Groups.GUEST},
                permissions__codename__in=MODEL_NODEGROUP_PERMS,
            ).values_list("name", flat=True)
        )

    @staticmethod
    def _assignments(slug, groups_by_name, deny_groups):
        """Every nodegroup perm to assign for one graph and the group to assign
        it to: what the policy grants, plus a denial for each group it skips."""
        by_group = nodegroup_perms(slug)
        by_group |= {name: {NO_ACCESS} for name in deny_groups - set(by_group)}
        for name, perms in by_group.items():
            if name in groups_by_name:
                for perm in perms:
                    yield perm, groups_by_name[name]

    @staticmethod
    def _clear_nodegroup_perms(nodegroups):
        """Strip every group and per-user grant off these nodegroups so the
        policy is the only grant; owner access is implicit. Perms set in the
        arches UI would otherwise route around default-deny."""
        content_type = ContentType.objects.get_for_model(NodeGroup)
        object_pks = [str(nodegroup.pk) for nodegroup in nodegroups]
        for model in (GroupObjectPermission, UserObjectPermission):
            model.objects.filter(
                content_type=content_type, object_pk__in=object_pks
            ).delete()
