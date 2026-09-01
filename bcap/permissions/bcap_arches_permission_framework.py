"""Default-deny framework, installed as PERMISSION_FRAMEWORK so every arches
path touching resources runs through it. Who may reach what is PERMISSION_DEFAULTS
in permission_settings.py; route access is separate again, through the DRF
permission classes on the views.
"""

from arches.app.permissions.arches_default_deny import (
    ArchesDefaultDenyPermissionFramework,
)

ANONYMOUS_USERNAME = "anonymous"


class BcapArchesPermissionFramework(ArchesDefaultDenyPermissionFramework):
    def user_is_resource_reviewer(self, user):
        """Signed-in users author for real; the public user keeps the stock
        check. A non-reviewer's tile save lands in provisionaledits with the
        tile written empty, and BCAP has no approval step."""
        if user.is_authenticated and user.username != ANONYMOUS_USERNAME:
            return True
        return super().user_is_resource_reviewer(user)
