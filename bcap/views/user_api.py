"""User-profile API endpoint.

Same thin view → serializer layering and drf-spectacular self-documentation
as the dashboard API (see ``bcap.views.dashboard_api`` for the full rationale).
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from arches.app.models import models

from bcap.serializers.dashboard_serializers import UserProfileResponseSerializer


class UserProfile(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["External: user_profile"],
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
