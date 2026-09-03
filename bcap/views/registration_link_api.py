"""Admin registration-link API plus the invitee's claim entry point.

Issuing links and the role-group lookup are admin-only JSON endpoints.
Claiming is an anonymous GET that stashes the token in the session and
bounces the visitor into login; redemption happens server-side on the
user_logged_in signal."""

from urllib.parse import urlsplit

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from bcap.permissions.groups import SELF_MANAGE_ROLE_GROUPS
from bcap.serializers.registration_serializers import (
    RegistrationLinkRequestSerializer,
    RegistrationLinkResponseSerializer,
)
from bcap.services.registration.invitation_registration_service import (
    PENDING_REGISTRATION_SESSION_KEY,
    InvitationRegistrationService,
)


@extend_schema(tags=["Admin: registration"])
class RegistrationLinkView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    @extend_schema(
        request=RegistrationLinkRequestSerializer,
        responses=RegistrationLinkResponseSerializer,
        description="Issue a single-use signup link for a Contributor.",
    )
    def post(self, request):
        serializer = RegistrationLinkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        body = serializer.validated_data
        link = InvitationRegistrationService().issue_link(
            request.user,
            contributor_id=body.contributor_id,
            new_contributor=body.new_contributor,
            groups=body.groups,
        )
        origin = urlsplit(settings.PUBLIC_SERVER_ADDRESS)
        path = f"{reverse('registration_claim')}?token={link.id}"
        signup_url = f"{origin.scheme}://{origin.netloc}{path}"
        return Response({"signup_url": signup_url, "expires": link.expires}, status=201)


@extend_schema(tags=["Admin: registration"])
class AssignableGroupsView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    @extend_schema(
        description="Role group names an invited user can be granted.",
        responses={200: {"type": "array", "items": {"type": "string"}}},
    )
    def get(self, request):
        return Response(SELF_MANAGE_ROLE_GROUPS)


@extend_schema(tags=["Admin: registration"])
class RegistrationClaimView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def get(self, request):
        """Stash the link token and bounce into IDIR login. Redemption happens
        server-side in the OAuth callback once authenticated."""
        token = request.GET.get("token")
        if token:
            request.session[PENDING_REGISTRATION_SESSION_KEY] = token
        response = redirect(reverse("auth"))
        # Keep the token (a query param) out of the Referer sent to the IDP.
        response["Referrer-Policy"] = "no-referrer"
        return response
