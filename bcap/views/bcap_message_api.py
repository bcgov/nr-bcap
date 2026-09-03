"""BCAP Message API views: a resource's threads, one thread's messages, and the
collection endpoint whose POST gates a new message on edit access to its
resource_context. The list views extend the generated arches_querysets view
(serialization and pagination come for free); query logic lives in
BcapMessageService."""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from arches_querysets.rest_framework.multipart_json_parser import MultiPartJSONParser
from arches_querysets.rest_framework.pagination import ArchesLimitOffsetPagination
from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin

from bcap.permissions.permit_resource_access import PermitResourceAccess
from bcap.permissions.route_permissions import SubmitterOrInternal
from bcap.serializers.bcap_message_serializers import (
    BcapMessagePatchSerializer,
    ModuleUnreadSerializer,
    ThreadMessageSerializer,
    ThreadRootSerializer,
    ThreadsQuerySerializer,
)
from bcap.serializers.contributor_serializers import ContributorSummarySerializer
from bcap.services.contributor.contributor_service import ContributorService
from bcap.services.message.bcap_message_service import (
    BcapMessageService,
    InternalMessageToExternal,
    NoAuthorContributor,
)
from bcap.views.generated.bcap_message import (
    BcapMessageListView,
    BcapMessageViewMixin,
)


@extend_schema(tags=["External: bcap_message"], parameters=[ThreadsQuerySerializer])
class BcapMessageThreadsView(BcapMessageViewMixin, ArchesModelAPIMixin, ListAPIView):
    """GET the threads on a parent resource, one per thread as its root
    (thread-starting) message, with the standard limit/offset pagination."""

    permission_classes = [SubmitterOrInternal]
    pagination_class = ArchesLimitOffsetPagination
    serializer_class = ThreadRootSerializer

    def get_queryset(self):
        params = ThreadsQuerySerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        PermitResourceAccess.require_view(
            self.request.user, str(self.kwargs["resource_id"])
        )
        return BcapMessageService().root_queryset(
            self.kwargs["resource_id"],
            self.request.user,
            archived=params.validated_data.archived,
        )


@extend_schema(tags=["External: bcap_message"])
class BcapMessageThreadView(BcapMessageViewMixin, ArchesModelAPIMixin, ListAPIView):
    """GET one thread's messages (its root and replies), oldest-first, with the
    standard limit/offset pagination the rest of the API uses."""

    permission_classes = [SubmitterOrInternal]
    pagination_class = ArchesLimitOffsetPagination
    serializer_class = ThreadMessageSerializer

    def get_queryset(self):
        service = BcapMessageService()
        thread_id = self.kwargs["thread_id"]
        PermitResourceAccess.require_view(
            self.request.user, service.message_resource_context_id(thread_id)
        )
        return service.thread_queryset(thread_id, self.request.user)


@extend_schema(tags=["External: bcap_message"])
class BcapMessageCreateView(BcapMessageListView):
    """The generated bcap_message collection endpoint, shadowed so POST first
    checks the caller may edit the resource the new message's resource_context
    points at. POST-only: reads go through the threads/messages endpoints."""

    parser_classes = [JSONParser, MultiPartJSONParser]

    def create(self, request, *args, **kwargs):
        service = BcapMessageService()
        attachments = request.FILES.getlist("attachments")
        if attachments:
            request.FILES.setlist(service.attachments_file_key(), attachments)
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
        PermitResourceAccess.require_change(request.user, resource_id)
        self.perform_create(serializer)
        # A reply resurfaces the thread
        service.unarchive_thread_for_all(serializer.instance.pk)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


@extend_schema(
    tags=["External: bcap_message"], responses=ModuleUnreadSerializer(many=True)
)
class BcapMessageModuleUnreadView(APIView):
    """GET the viewer's unread count per process_module of a submission, so the
    module list badges unread without loading each module's threads. The counts
    are the caller's own; the gate is on the submission they ask about."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [SubmitterOrInternal]

    def get(self, request, submission_id):
        PermitResourceAccess.require_view(request.user, str(submission_id))
        rows = BcapMessageService().unread_by_module(
            str(submission_id), request.user.username
        )
        return Response(ModuleUnreadSerializer(rows, many=True).data)


@extend_schema(
    tags=["External: bcap_message"],
    responses=ContributorSummarySerializer(many=True),
)
class BcapMessageContributorsView(APIView):
    """GET the contributors you can address a message to for a resource: the
    login-linked contributors referenced on it plus its ministry assignees.
    Gated on read access to the resource, like the threads on it."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [SubmitterOrInternal]

    def get(self, request, resource_id):
        PermitResourceAccess.require_view(request.user, str(resource_id))
        options = ContributorService().contributors_for_resource(str(resource_id))
        return Response(ContributorSummarySerializer(options, many=True).data)


@extend_schema(tags=["External: bcap_message"])
@extend_schema_view(patch=extend_schema(request=BcapMessagePatchSerializer))
class BcapMessageDetailView(
    BcapMessageViewMixin, ArchesModelAPIMixin, RetrieveUpdateAPIView
):
    """GET or PATCH a single message, gated on the resource_context rather than
    owner-scoped: reading it needs read access, PATCH needs edit access. PATCH
    sets the read date (message_read_date in the body) and/or the caller's
    personal archive of the thread (a top-level "archived" boolean), whichever
    the body carries."""

    permission_classes = [SubmitterOrInternal]
    http_method_names = ["get", "patch", "options"]

    def _context_id(self):
        return BcapMessageService().message_resource_context_id(self.kwargs["pk"])

    def retrieve(self, request, *args, **kwargs):
        PermitResourceAccess.require_view(request.user, self._context_id())
        return Response(self.get_serializer(self.get_object()).data)

    def update(self, request, *args, **kwargs):
        PermitResourceAccess.require_change(request.user, self._context_id())
        service = BcapMessageService()
        # A PATCH can carry the read date, the archive flag, either, or both; each
        # setter no-ops when its own field is absent from the body.
        service.set_read_state(request, self.kwargs["pk"], request.data)
        service.set_archived_state(
            self.kwargs["pk"], request.data, request.user.username
        )
        return Response(self.get_serializer(self.get_object()).data)
