"""Default-deny framework, installed as PERMISSION_FRAMEWORK so every arches
path touching resources runs through it. Who may reach what is
PERMISSION_DEFAULTS in permission_settings.py; object ownership is enforced
separately again, by the user-owned queryset filter.

An instance check arrives here from a route: a view asks the arches permission
backend, which dispatches to this class. The stock policy answers first, then
an applicant's answer is narrowed by the permit reach check in
permit_access. That module also holds the helpers views call directly,
and those do ask the policy, so the narrowing here must use the reach check
rather than a helper or it would arrive back at this method and recurse.
"""

from arches.app.permissions.arches_default_deny import (
    ArchesDefaultDenyPermissionFramework,
)

from bcap.permissions.groups import Groups, group_id, is_internal_user
from bcap.permissions.permit_access import PermitAccess

ANONYMOUS_USERNAME = "anonymous"


class BcapArchesPermissionFramework(ArchesDefaultDenyPermissionFramework):
    def check_resource_instance_permissions(
        self, user, resourceid, permission, *, resource=None
    ):
        """The graph policy grants an applicant a whole graph; narrow that to
        the instances their own permits reach. Narrowing applies wherever the
        policy said yes, since arches permits a resource's creator ahead of any
        grant, and reach rather than authorship is what governs an applicant."""
        result = super().check_resource_instance_permissions(
            user, resourceid, permission, resource=resource
        )
        if result.get("permitted") and not is_internal_user(user):
            result["permitted"] = PermitAccess.on_visible_permit_or_draft(
                user, result["resource"].pk
            )
        return result

    def get_index_values(self, resource, **kwargs):
        """Keep the applicant grant out of the search index. The index matches
        on group id alone, with no room for the check above, so leaving
        Submitter on it would show every applicant every other's permits.

        TODO: in the future it might be possible to expand this to owning organizations,
        but I think we're hiding the search for submitters for now."""
        values = super().get_index_values(resource, **kwargs)
        submitter_id = group_id(Groups.SUBMITTER)
        for key in ("groups_read", "groups_edit"):
            values[key] = [gid for gid in values[key] if gid != submitter_id]
        return values

    def user_is_resource_reviewer(self, user):
        """Signed-in users author for real; the public user keeps the stock
        check. A non-reviewer's tile save lands in provisionaledits with the
        tile written empty, and BCAP has no approval step, so narrowing this to
        a role loses that role's edits silently rather than refusing them.

        TODO: arches gates the lifecycle-state POST on this call alone, with no
        ownership check after it, so an applicant can change any resource's
        state by id. Shadow that route ahead of the arches include.
        In the future we want to make this resource based,
        but I'm not sure if it's possible to do this way.
        """
        if user.is_authenticated and user.username != ANONYMOUS_USERNAME:
            return True
        return super().user_is_resource_reviewer(user)
