"""BCAP Message API views: a resource's threads, one thread's messages, and the
collection endpoint whose POST gates a new message on edit access to its
resource_context. The list views extend the generated arches_querysets view
(serialization and pagination come for free); query logic lives in
BcapMessageService."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from arches.app.utils.permission_backend import user_can_edit_resource
from arches_querysets.rest_framework.multipart_json_parser import MultiPartJSONParser
from arches_querysets.rest_framework.pagination import ArchesLimitOffsetPagination
from arches_querysets.rest_framework.permissions import ReadOnly, ResourceEditor
from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin

from rest_framework_dataclasses.serializers import DataclassSerializer

from bcap.services.contributor_service import (
    ContributorSummary,
    ContributorService,
)
from bcap.services.message.bcap_message_service import (
    BcapMessageService,
    InternalMessageToExternal,
    NoAuthorContributor,
)
from bcap.views.generated.bcap_message import (
    BcapMessageListView,
    BcapMessageViewMixin,
)


@extend_schema(tags=["External: bcap_message"])
class BcapMessageThreadsView(BcapMessageViewMixin, ArchesModelAPIMixin, ListAPIView):
    """GET the threads on a parent resource, one per thread as its root
    (thread-starting) message, with the standard limit/offset pagination."""

    permission_classes = [ResourceEditor | ReadOnly]
    pagination_class = ArchesLimitOffsetPagination

    def get_queryset(self):
        return BcapMessageService().root_queryset(
            self.kwargs["resource_id"], self.request.user
        )


@extend_schema(tags=["External: bcap_message"])
class BcapMessageThreadView(BcapMessageViewMixin, ArchesModelAPIMixin, ListAPIView):
    """GET one thread's messages (its root and replies), oldest-first, with the
    standard limit/offset pagination the rest of the API uses."""

    permission_classes = [ResourceEditor | ReadOnly]
    pagination_class = ArchesLimitOffsetPagination

    def get_queryset(self):
        return BcapMessageService().thread_queryset(
            self.kwargs["thread_id"], self.request.user
        )


@extend_schema(tags=["External: bcap_message"])
class BcapMessageCreateView(BcapMessageListView):
    """The generated bcap_message collection endpoint, shadowed so POST first
    checks the caller may edit the resource the new message's resource_context
    points at. POST-only: reads go through the threads/messages endpoints."""

    parser_classes = [JSONParser, MultiPartJSONParser]

    def create(self, request, *args, **kwargs):
        service = BcapMessageService()
        try:
            service.prepare_message(request.data, request.user)
        except NoAuthorContributor:
            raise ValidationError(
                "No Contributor is linked to your account to author this message."
            )
        except InternalMessageToExternal:
            raise ValidationError(
                "An internal message cannot be addressed to an external recipient."
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resource_id = service.resource_context_id(request.data)
        if not user_can_edit_resource(request.user, resourceid=resource_id):
            raise PermissionDenied("No access to the resource context.")
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class ContributorSummarySerializer(DataclassSerializer):
    class Meta:
        dataclass = ContributorSummary


@extend_schema(
    tags=["External: bcap_message"],
    responses=ContributorSummarySerializer(many=True),
)
class BcapMessageContributorsView(APIView):
    """GET the contributors you can address a message to for a resource: the
    login-linked contributors referenced on it plus its ministry assignees.
    Gated on edit access to the resource, like posting a message about it."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, resource_id):
        if not user_can_edit_resource(request.user, resourceid=str(resource_id)):
            raise PermissionDenied("No access to the resource context.")
        options = ContributorService().contributors_for_resource(str(resource_id))
        return Response(ContributorSummarySerializer(options, many=True).data)


@extend_schema(tags=["External: bcap_message"])
class BcapMessageDetailView(
    BcapMessageViewMixin, ArchesModelAPIMixin, RetrieveUpdateAPIView
):
    """GET or PATCH a single message, both gated like create (edit access to the
    resource_context, not owner-scoped). PATCH writes only message_read_date."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "options"]

    def _require_context_edit(self, request):
        service = BcapMessageService()
        resource_id = service.message_resource_context_id(self.kwargs["pk"])
        if not user_can_edit_resource(request.user, resourceid=resource_id):
            raise PermissionDenied("No access to the resource context.")

    def retrieve(self, request, *args, **kwargs):
        self._require_context_edit(request)
        return Response(self.get_serializer(self.get_object()).data)

    def update(self, request, *args, **kwargs):
        self._require_context_edit(request)
        BcapMessageService().set_read_state(self.kwargs["pk"], request.data)
        return Response(self.get_serializer(self.get_object()).data)
