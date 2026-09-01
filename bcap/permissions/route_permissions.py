"""DRF route permission helpers, for custom BCAP endpoints as much as for the
standard arches ones. Group names come from groups.py, so the route gate and the
data-layer framework refer to the same groups.

These gate which role may reach an endpoint; object ownership is enforced
separately by the user-owned queryset filter.
"""

from rest_framework import permissions

from arches.app.utils.permission_backend import group_required

from bcap.permissions.groups import Groups, INTERNAL_GROUPS


def any_groups_required(*group_names):
    """A DRF permission passing if the user is in any of the named groups."""

    class _RolesRequired(permissions.BasePermission):
        def has_permission(self, request, view):
            return bool(group_required(request.user, *group_names))

    return _RolesRequired


Submitter = any_groups_required(Groups.SUBMITTER)
Internal = any_groups_required(*INTERNAL_GROUPS)
SubmitterOrInternal = any_groups_required(Groups.SUBMITTER, *INTERNAL_GROUPS)
