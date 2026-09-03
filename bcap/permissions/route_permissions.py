"""Route permission helpers, for custom BCAP endpoints as much as for the
standard arches ones. Group names come from groups.py, so the route gate and the
data-layer framework refer to the same groups.

These gate which role may reach an endpoint; object ownership is enforced
separately by the user-owned queryset filter.
"""

from django.utils.decorators import method_decorator
from rest_framework import permissions

from arches.app.utils.decorators import group_required as group_required_decorator
from arches.app.utils.permission_backend import group_required

from bcap.permissions.groups import Groups, INTERNAL_GROUPS


def any_groups_required(*group_names):
    """A DRF permission passing if the user is in any of the named groups."""

    class _RolesRequired(permissions.BasePermission):
        def has_permission(self, request, view):
            return bool(group_required(request.user, *group_names))

    return _RolesRequired


def any_groups_required_django_view(*group_names, raise_exception=False):
    """Class decorator for plain Django views, which ignore permission_classes.
    Without raise_exception a denied user is redirected to login rather than
    given a 403, which suits browser pages but not JSON endpoints."""
    return method_decorator(
        group_required_decorator(*group_names, raise_exception=raise_exception),
        name="dispatch",
    )


class InternalWrites(permissions.BasePermission):
    """Reads for whoever the route's other gates let in; writes for ministry
    staff only. Pair it with the gate naming who may read."""

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS or bool(
            group_required(request.user, *INTERNAL_GROUPS)
        )


Submitter = any_groups_required(Groups.SUBMITTER)
Internal = any_groups_required(*INTERNAL_GROUPS)
SubmitterOrInternal = any_groups_required(Groups.SUBMITTER, *INTERNAL_GROUPS)

internal_only_django_view = any_groups_required_django_view(
    *INTERNAL_GROUPS, raise_exception=True
)
resource_editor_only_django_view = any_groups_required_django_view(
    Groups.RESOURCE_EDITOR
)
resource_exporter_only_function_view = group_required_decorator(
    Groups.RESOURCE_EXPORTER
)
