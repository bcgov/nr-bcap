"""Dashboard / user-profile API endpoints.

Approach:
- Thin view → serializer → service layering. Views only validate input,
  call a service, and serialize output; business logic lives in
  ``bcap.services`` and the API contract lives in
  ``bcap.serializers.dashboard_serializers``.
- Built on Django REST Framework (not django-ninja) for consistency with
  Arches, which is itself a DRF application. This lets us reuse Arches'
  ``SessionAuthentication`` (the existing logged-in cookie) and share its
  auth/permission machinery instead of running a parallel API stack.
- Self-documenting via drf-spectacular: ``@extend_schema`` + the serializers
  generate the OpenAPI spec, scoped to bcap-only routes through
  ``bcap.documented_api_urls`` (Arches serializers break introspection).
- Contract chain: DRF serializer → ``schema.yml`` → ``api-types.ts``, giving
  the Vue frontend generated TypeScript types from a single source of truth.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from drf_spectacular.utils import extend_schema

from arches.app.models import models

from bcap.serializers.dashboard_serializers import (
    UserProfileResponseSerializer,
    DashboardCardResponseSerializer,
    DashboardQuerySerializer,
)
from bcap.services.dashboard_service import DashboardQuery, DashboardService


class UserProfile(APIView):
    authentication_classes = [SessionAuthentication]

    @extend_schema(
        responses=UserProfileResponseSerializer,
        description=(
            "Returns the authenticated user's profile, group "
            "memberships, and linked Contributor resource id."
        ),
    )
    def get(self, request):
        user_profile = models.User.objects.get(id=request.user.pk)
        serializer = UserProfileResponseSerializer(user_profile)
        return Response(serializer.data)


class DashboardView(APIView):
    """Returns dashboard cards for the current user based on their role."""

    authentication_classes = [SessionAuthentication]

    @extend_schema(
        parameters=[DashboardQuerySerializer],
        responses=DashboardCardResponseSerializer(many=True),
    )
    def get(self, request):
        query = DashboardQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        cards = DashboardService().get_cards(DashboardQuery(**query.validated_data))
        return Response(DashboardCardResponseSerializer(cards, many=True).data)
