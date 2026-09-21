"""BCAP Message API views: a resource's threads, one thread's messages, and the
collection endpoint whose POST gates a new message on edit access to its
resource_context. The list views extend the generated arches_querysets view
(serialization and pagination come for free); query logic lives in
BcapMessageService."""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from arches_querysets.rest_framework.multipart_json_parser import MultiPartJSONParser
from arches_querysets.rest_framework.pagination import ArchesLimitOffsetPagination
from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin

from bcap.permissions.route_guards import SubmitterOrInternal
from bcap.serializers.bcap_message_serializers import (
    BcapMessagePatchSerializer,
    ModuleUnresolvedSerializer,
    ThreadRootSerializer,
    ThreadsQuerySerializer,
)
from bcap.serializers.contributor_serializers import ContributorSummarySerializer
from bcap.services.message.bcap_message_service import (
    BcapMessageService,
    NoAuthorContributor,
)
from bcap.services.message.message_context import MessageGraph
from bcap.util.aliases.bcap_message import BcapMessageAliases as A
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
        return BcapMessageService().thread_roots_query(
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

    def get_queryset(self):
        return BcapMessageService().thread_messages_query(
            self.kwargs["thread_id"], self.request.user
        )


@extend_schema(tags=["External: bcap_message"])
class BcapMessageCreateView(BcapMessageListView):
    """The generated bcap_message collection endpoint, shadowed so POST first
    checks the caller may edit the resource the new message's resource_context
    points at. POST-only: reads go through the threads/messages endpoints."""

    parser_classes = [JSONParser, MultiPartJSONParser]

    def create(self, request, *args, **kwargs):
        """Ready the body before the standard create validates it: the author and
        the reply fields are stamped onto it, so validating any earlier would save
        a message without them."""
        # Clients upload as "attachments"; the file-list datatype reads its own key.
        attachments = request.FILES.getlist("attachments")
        if attachments:
            request.FILES.setlist(
                f"file-list_{MessageGraph.node(A.ATTACHMENTS)}", attachments
            )
        try:
            BcapMessageService().prepare_create_payload(request.data, request.user)
        except NoAuthorContributor:
            raise ValidationError(
                "No Contributor is linked to your account to author this message."
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """A new message reopens the thread for the other side and resurfaces it
        for everyone party to it."""
        super().perform_create(serializer)
        service = BcapMessageService()
        service.update_resolutions_after_post(serializer.instance.pk, self.request.user)
        service.unarchive_for_everyone(serializer.instance.pk)


@extend_schema(
    tags=["External: bcap_message"], responses=ModuleUnresolvedSerializer(many=True)
)
class BcapMessageModuleUnresolvedView(APIView):
    """GET the viewer's unresolved thread count per process_module of a
    submission, so the module list badges them without loading each module's
    threads."""

    permission_classes = [SubmitterOrInternal]

    def get(self, request, submission_id):
        rows = BcapMessageService().unresolved_counts_by_module(
            str(submission_id), request.user
        )
        return Response(ModuleUnresolvedSerializer(rows, many=True).data)


@extend_schema(
    tags=["External: bcap_message"],
    responses=ContributorSummarySerializer(many=True),
)
class BcapMessageContributorsView(APIView):
    """GET the contributors you can address a message to for a resource: the
    login-linked contributors referenced on it and its ministry assignees, or
    the Archaeology Branch when there are none; staff also get whoever filed
    the permit."""

    permission_classes = [SubmitterOrInternal]

    def get(self, request, resource_id):
        options = BcapMessageService().recipient_options(resource_id, request.user)
        return Response(ContributorSummarySerializer(options, many=True).data)


@extend_schema(tags=["External: bcap_message"])
@extend_schema_view(patch=extend_schema(request=BcapMessagePatchSerializer))
class BcapMessageDetailView(
    BcapMessageViewMixin, ArchesModelAPIMixin, RetrieveUpdateAPIView
):
    """GET or PATCH a single message, gated on the resource_context rather than
    owner-scoped: reading it needs read access, PATCH needs edit access. PATCH
    resolves or reopens the thread for everyone ("resolved") and/or toggles the
    caller's personal archive of it ("archived"), whichever the body carries."""

    permission_classes = [SubmitterOrInternal]
    http_method_names = ["get", "patch", "options"]

    def get_queryset(self):
        """Narrowed like the thread listing, and gated in the same call: the
        resource_context says whose correspondence this is, not which of it the
        caller is party to."""
        return BcapMessageService.detail_query(self.kwargs["pk"], self.request.user)

    def update(self, request, *args, **kwargs):
        self.get_object()
        BcapMessageService().update_thread_state(
            request.user, self.kwargs["pk"], request.data
        )
        return Response(self.get_serializer(self.get_object()).data)
