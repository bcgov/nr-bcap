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
    ModuleUnreadSerializer,
    ThreadMessageSerializer,
    ThreadRootSerializer,
    ThreadsQuerySerializer,
)
from bcap.serializers.contributor_serializers import ContributorSummarySerializer
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
    serializer_class = ThreadMessageSerializer

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
        try:
            BcapMessageService().prepare_message(
                request.data, request.user, request.FILES
            )
        except NoAuthorContributor:
            raise ValidationError(
                "No Contributor is linked to your account to author this message."
            )
        except InternalMessageToExternal:
            raise ValidationError(
                "An internal message cannot be addressed to an external recipient."
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """A reply resurfaces the thread for everyone party to it."""
        super().perform_create(serializer)
        BcapMessageService().unarchive_thread_for_all(serializer.instance.pk)


@extend_schema(
    tags=["External: bcap_message"], responses=ModuleUnreadSerializer(many=True)
)
class BcapMessageModuleUnreadView(APIView):
    """GET the viewer's unread count per process_module of a submission, so the
    module list badges unread without loading each module's threads."""

    permission_classes = [SubmitterOrInternal]

    def get(self, request, submission_id):
        rows = BcapMessageService().unread_by_module(str(submission_id), request.user)
        return Response(ModuleUnreadSerializer(rows, many=True).data)


@extend_schema(
    tags=["External: bcap_message"],
    responses=ContributorSummarySerializer(many=True),
)
class BcapMessageContributorsView(APIView):
    """GET the contributors you can address a message to for a resource: the
    login-linked contributors referenced on it plus its ministry assignees."""

    permission_classes = [SubmitterOrInternal]

    def get(self, request, resource_id):
        options = BcapMessageService().addressable_contributors(
            resource_id, request.user
        )
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

    def get_queryset(self):
        """Narrowed like the thread listing, and gated in the same call: the
        resource_context says whose correspondence this is, not which of it the
        caller is party to."""
        return BcapMessageService.detail_query(self.kwargs["pk"], self.request.user)

    def update(self, request, *args, **kwargs):
        self.get_object()
        BcapMessageService().apply_patch(request, self.kwargs["pk"], request.data)
        return Response(self.get_serializer(self.get_object()).data)
