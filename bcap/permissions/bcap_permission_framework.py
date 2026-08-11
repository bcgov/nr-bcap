"""Permission framework for BCAP: default-allow, minus the provisional-edit path.

Arches holds a tile save by anyone outside the Resource Reviewer group as a
provisional edit -- the values are parked in provisionaledits and the tile is
written empty until a reviewer approves it. BCAP has no approval step, and its
applicants author their own drafts, messages and submissions, so every signed-in
user's edits are authoritative. Group membership itself is left alone.

Arches gates a few things on this same check, so they widen to every signed-in
user: core's lifecycle-state POST (api/resource_instance_lifecycle_state), which
BCAP should re-gate to staff, its get_user_names lookup, and the visibility of
edits awaiting approval, which is moot while nothing is provisional.
"""

from arches.app.permissions.arches_default_allow import (
    ArchesDefaultAllowPermissionFramework,
)

ANONYMOUS_USERNAME = "anonymous"


class BcapPermissionFramework(ArchesDefaultAllowPermissionFramework):
    def user_is_resource_reviewer(self, user):
        """Signed-in users author for real; the public user keeps the stock check."""
        if user.is_authenticated and user.username != ANONYMOUS_USERNAME:
            return True
        return super().user_is_resource_reviewer(user)
