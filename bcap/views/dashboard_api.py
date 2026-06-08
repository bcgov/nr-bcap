"""Dashboard / user-profile API endpoints.

Thin views: validate input, call a service, serialize output. Built on DRF
(like Arches) so we reuse its session auth, and drf-spectacular generates the
OpenAPI spec that feeds the frontend's generated TypeScript types.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from drf_spectacular.utils import extend_schema

from bcap.serializers.dashboard_serializers import (
    DashboardPageResponseSerializer,
    DashboardFilterSerializer,
)
from bcap.services.dashboard.dashboard_service import DashboardService


class DashboardView(APIView):
    """Returns dashboard cards for the current user based on their role."""

    authentication_classes = [SessionAuthentication]

    @extend_schema(
        tags=["Internal: dashboard"],
        parameters=[DashboardFilterSerializer],
        responses=DashboardPageResponseSerializer,
    )
    def get(self, request):
        query = DashboardFilterSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        page = DashboardService().get_cards(query.validated_data, request.user.username)
        return Response(DashboardPageResponseSerializer(page).data)
