"""Dashboard / user-profile API endpoints.

Thin views: validate input, call a service, serialize output. Built on DRF
(like Arches) so we reuse its session auth, and drf-spectacular generates the
OpenAPI spec that feeds the frontend's generated TypeScript types.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from drf_spectacular.utils import extend_schema

from bcap.permissions.route_permissions import Internal, SubmitterOrInternal
from bcap.serializers.dashboard_serializers import (
    InternalDashboardPageResponseSerializer,
    InternalDashboardFilterSerializer,
    ExternalDashboardFilterSerializer,
    ExternalDashboardPageResponseSerializer,
)
from bcap.services.dashboard.internal_dashboard_service import (
    InternalDashboardService,
)
from bcap.services.dashboard.external_dashboard_service import (
    ExternalDashboardService,
)


class InternalDashboardView(APIView):
    """Returns dashboard cards for the current user based on their role."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [Internal]

    @extend_schema(
        tags=["Internal: dashboard"],
        parameters=[InternalDashboardFilterSerializer],
        responses=InternalDashboardPageResponseSerializer,
    )
    def get(self, request):
        query = InternalDashboardFilterSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        page = InternalDashboardService().get_cards(
            query.validated_data, request.user.username
        )
        return Response(InternalDashboardPageResponseSerializer(page).data)


class ExternalDashboardView(APIView):
    """The applicant-facing dashboard: cards for the requesting user's own and
    their associated companies' permit applications (and their drafts), scoped by
    created-by.

    The gate only says who may ask: isolation between applicants is the
    service's queryset filter alone, so a query added without it leaks.

    TODO: staff are not widened here the way they are on the permit routes --
    the filter treats them as an applicant, so they see only what they filed
    themselves. Temporary, pending the decision on what staff should see here."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [SubmitterOrInternal]

    @extend_schema(
        tags=["External: dashboard"],
        parameters=[ExternalDashboardFilterSerializer],
        responses=ExternalDashboardPageResponseSerializer,
    )
    def get(self, request):
        query = ExternalDashboardFilterSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        page = ExternalDashboardService().get_cards(query.validated_data, request.user)
        return Response(ExternalDashboardPageResponseSerializer(page).data)
