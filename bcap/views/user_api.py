"""User-profile API endpoint.

The response comes from bcgov_arches_common; the route's gate and its OpenAPI
entry are BCAP's, since the shared package carries no drf-spectacular.
"""

from drf_spectacular.utils import extend_schema

from bcgov_arches_common.views.api.user import (
    UserResponseSerializer,
    UserView,
)

from bcap.permissions.route_guards import SubmitterOrInternal


@extend_schema(
    tags=["External: user"],
    responses=UserResponseSerializer,
    description=(
        "Returns the authenticated user's name, group memberships, and "
        "whether they are a superuser."
    ),
)
class BCAPUserView(UserView):
    permission_classes = [SubmitterOrInternal]
