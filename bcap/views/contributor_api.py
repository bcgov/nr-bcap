"""Contributor lookups that aren't plain graph reads: the pick-lists staff
screens need. The owner-scoped resource routes are generated (see
bcap.views.generated.contributor)."""

from drf_spectacular.utils import extend_schema
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from bcap.serializers.registration_serializers import ContributorSummarySerializer
from bcap.services.contributor_service import ContributorService
from bcap.views.process_requirement_api import STAFF_MODULE_PERMISSIONS


@extend_schema(tags=["Internal: contributor"])
class AssignableContributorsView(APIView):
    """GET the Contributors work can be assigned to."""

    authentication_classes = [SessionAuthentication]
    permission_classes = STAFF_MODULE_PERMISSIONS

    @extend_schema(responses=ContributorSummarySerializer(many=True))
    def get(self, request):
        options = ContributorService().assignable_contributors()
        return Response(ContributorSummarySerializer(options, many=True).data)


@extend_schema(tags=["Admin: registration"])
class UnlinkedContributorsView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    @extend_schema(
        responses=ContributorSummarySerializer(many=True),
        description="Contributors not yet linked to a user account.",
    )
    def get(self, request):
        options = ContributorService().invitable_contributors(
            request.GET.get("search", "")
        )
        return Response(ContributorSummarySerializer(options, many=True).data)
