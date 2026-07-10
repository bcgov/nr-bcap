"""BCAP Message API views: a resource's threads, one thread's messages, and the
collection endpoint whose POST gates a new message on edit access to its
resource_context. The list views extend the generated arches_querysets view
(serialization and pagination come for free); query logic lives in
BcapMessageService."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView, UpdateAPIView
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from arches.app.utils.permission_backend import user_can_edit_resource
from arches_querysets.rest_framework.multipart_json_parser import MultiPartJSONParser
from arches_querysets.rest_framework.pagination import ArchesLimitOffsetPagination
from arches_querysets.rest_framework.permissions import ReadOnly, ResourceEditor
from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin

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


@extend_schema(tags=["External: bcap_message"])
class BcapMessageUpdateView(BcapMessageViewMixin, ArchesModelAPIMixin, UpdateAPIView):
    """PATCH a message's read state, gated like create (edit access to the
    resource_context, not owner-scoped). Only message_read_date is written."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["patch", "options"]

    def update(self, request, *args, **kwargs):
        service = BcapMessageService()
        message_id = self.kwargs["pk"]
        resource_id = service.message_resource_context_id(message_id)
        if not user_can_edit_resource(request.user, resourceid=resource_id):
            raise PermissionDenied("No access to the resource context.")
        service.set_read_state(message_id, request.data)
        return Response(self.get_serializer(self.get_object()).data)
