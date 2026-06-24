"""Permit Application CRUD via arches_querysets' generic resource serializer:
POST a new application, and GET/PUT/PATCH/DELETE an existing one."""

from drf_spectacular.utils import extend_schema
from rest_framework.generics import CreateAPIView
from rest_framework.parsers import JSONParser

from arches_querysets.rest_framework.generic_views import (
    ArchesResourceDetailView,
    ArchesModelAPIMixin,
)
from arches_querysets.rest_framework.permissions import ResourceEditor

from bcap.services.permit_application.permit_application_service import (
    PermitApplicationService,
)
from bcap.views.mixins import (
    ArchesResourceViewMixin,
    UserOwnedResourceMixin,
)

from bcap.views.generated.permit_application import PermitApplicationSerializer


class PermitApplicationViewMixin(ArchesResourceViewMixin):
    serializer_class = PermitApplicationSerializer


@extend_schema(tags=["External: permit_application"])
class PermitApplicationView(
    PermitApplicationViewMixin, UserOwnedResourceMixin, ArchesResourceDetailView
):
    """GET/PUT/PATCH/DELETE a Permit Application and its nested tiles.

    Scoped to the requesting user's own applications: requesting one created by
    another user returns 404.

    The update that first sets the submission date is the submission: it
    assigns the application id and attaches the requirement working copies.

    PATCH applies a partial diff (only the tiles present in the body); PUT
    replaces.
    """

    def update(self, request, *args, **kwargs):
        return PermitApplicationService().submit(
            self.get_object(),
            request.data,
            save=lambda: super(PermitApplicationView, self).update(
                request, *args, **kwargs
            ),
        )


@extend_schema(tags=["External: permit_application"])
class PermitApplicationCreateView(
    PermitApplicationViewMixin, ArchesModelAPIMixin, CreateAPIView
):
    """POST a new Permit Application, seeding its application id.

    Create-only: CreateAPIView exposes just POST (and OPTIONS); there is no
    list/GET route. The requirements are attached later, on submission (see the
    detail view).
    """

    permission_classes = [ResourceEditor]
    parser_classes = [JSONParser]
    http_method_names = ["post", "options"]

    def create(self, request, *args, **kwargs):
        return PermitApplicationService().create(
            request.data,
            save=lambda: super(PermitApplicationCreateView, self).create(
                request, *args, **kwargs
            ),
        )
