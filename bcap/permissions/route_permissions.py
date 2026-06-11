"""BCAP-specific DRF route permission helpers. Role names come from groups.py
so the route gate and the data-layer framework refer to the same groups.
``any_groups_required()`` builds a permission that passes if the user is in any
of the named groups; compose ad-hoc sets at the view, e.g.
``any_groups_required(Groups.SUBMITTER, Groups.RESOURCE_EDITOR)``.

These gate *which role may reach an endpoint*; object ownership is enforced
separately by the user-owned queryset filter.
"""

from rest_framework import permissions

from arches.app.utils.permission_backend import group_required

from bcap.permissions.groups import Groups


def any_groups_required(*group_names):
    """A DRF permission passing if the user is in any of the named groups."""

    class _RolesRequired(permissions.BasePermission):
        def has_permission(self, request, view):
            return bool(group_required(request.user, *group_names))

    return _RolesRequired


# Internal staff roles, listed explicitly (everyone who isn't Guest/Submitter).
INTERNAL_GROUPS = (
    Groups.ARCHAEOLOGY_BRANCH,
    Groups.RESOURCE_EDITOR,
    Groups.RESOURCE_REVIEWER,
    Groups.RESOURCE_EXPORTER,
    Groups.PERMIT_REVIEWER,
    Groups.PERMIT_DECIDER,
    Groups.INVENTORY_REVIEWER,
    Groups.INVENTORY_MANAGER,
)

# The external public-submission role.
Submitter = any_groups_required(Groups.SUBMITTER)

# Any internal/staff role.
Internal = any_groups_required(*INTERNAL_GROUPS)
