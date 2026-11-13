"""BCAP Service Request CRUD: seed the service request id on create, and
attach the requirement working copies on first submission.

The create view subclasses the generated view components rather than the
generated view class itself (which is GET-only) so the create path can live
at the same URL prefix without disabling the generated list.

The detail view subclasses the generated RetrieveAPIView and adds PATCH so
submissions can be processed here.
"""

from drf_spectacular.utils import extend_schema
from rest_framework.generics import CreateAPIView

from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin

from bcap.permissions.route_guards import SubmitterOrInternal
from bcap.services.bcap_service_request.bcap_service_request_service import (
    BcapServiceRequestService,
)
from bcap.util.aliases.bcap_service_request import (
    BcapServiceRequestAliases as aliases,
    BcapServiceRequestGroupAliases as group_aliases,
)
from bcap.util.bcap_aliases import ALIASED_DATA, GraphSlugs
from bcap.util.reference_number import allocate_reference_number
from bcap.util.tiles import set_payload_node
from bcap.views.mixins import SanitizeFeatureIdsMixin
from bcap.views.generated.bcap_service_request import (
    BcapServiceRequestView as GeneratedBcapServiceRequestView,
    BcapServiceRequestViewMixin,
)


def _allocate_service_request_id():
    """Next SR-YYYY-NNNN reference number via the reference-number-widget service."""
    return allocate_reference_number(
        GraphSlugs.BCAP_SERVICE_REQUEST, aliases.SERVICE_REQUEST_ID
    )


def _seed_service_request_id(data):
    """Inject an SR-<n> id into service_request_id if the payload doesn't
    carry one. The node is required by the graph but is never filled by the
    user form; the backend owns its value."""
    ident = (
        (data.get(ALIASED_DATA) or {})
        .get(group_aliases.SERVICE_REQUEST_IDENTIFICATION, {})
        .get(ALIASED_DATA, {})
    )
    if not (ident.get(aliases.SERVICE_REQUEST_ID) or {}).get("node_value"):
        set_payload_node(
            data,
            group_aliases.SERVICE_REQUEST_IDENTIFICATION,
            aliases.SERVICE_REQUEST_ID,
            _allocate_service_request_id(),
        )


@extend_schema(tags=["External: bcap_service_request"])
class BcapServiceRequestView(SanitizeFeatureIdsMixin, GeneratedBcapServiceRequestView):
    """GET/PATCH a BCAP Service Request and its nested tiles.

    The update that first sets the submission date is the submission: it
    attaches the requirement working copies."""

    permission_classes = [SubmitterOrInternal]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return BcapServiceRequestService.base_query(
            self.request.user, resource_ids=self.resource_ids
        )

    def update(self, request, *args, **kwargs):
        def save():
            self.sanitize_all_feature_ids(request.data)
            return super(BcapServiceRequestView, self).update(request, *args, **kwargs)

        return BcapServiceRequestService(request).submit(
            self.get_object(),
            request.data,
            request.user,
            save=save,
        )


@extend_schema(tags=["External: bcap_service_request"])
class BcapServiceRequestCreateView(
    SanitizeFeatureIdsMixin,
    BcapServiceRequestViewMixin,
    ArchesModelAPIMixin,
    CreateAPIView,
):
    """POST a new BCAP Service Request from a workflow draft payload.

    Sanitizes WFS GeoJSON feature IDs from the service_request_boundary before
    persisting, and seeds service_request_id (a backend-owned required node).
    A body that already carries the submission date attaches the requirement
    working copies here; one saved as a draft gets them on the update that
    submits it (see the detail view).

    Applicants file their own service requests, so this only asks for a login;
    owner-scoping is implicit (the resource is created by the requesting user)."""

    permission_classes = [SubmitterOrInternal]
    http_method_names = ["post", "options"]

    def create(self, request, *args, **kwargs):
        self.sanitize_all_feature_ids(request.data)
        _seed_service_request_id(request.data)

        def save():
            return super(BcapServiceRequestCreateView, self).create(
                request, *args, **kwargs
            )

        return BcapServiceRequestService(request).create(request.data, save=save)
