"""Permit Application CRUD: the generated owner-scoped views plus the business
rules that don't belong in codegen -- seed the application id on create, and
attach the requirement working copies on first submission.

These subclass the generated views and are registered (in
bcap.urls_api_documented) at the same paths as the generated routes, declared
first, so they shadow them.
"""

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated

from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin

from bcap.services.contributor.organization_service import OrganizationService
from bcap.services.permit_application.permit_application_service import (
    PermitApplicationService,
)
from bcap.util.aliases.permit_application import (
    PermitApplicationAliases as PA,
    PermitApplicationGroupAliases,
)
from bcap.views.organization_helpers import block_organization, stamp_organization
from bcap.views.generated.permit_application import (
    PermitApplicationListView as GeneratedPermitApplicationListView,
    PermitApplicationView as GeneratedPermitApplicationView,
)


@extend_schema(tags=["External: permit_application"])
class PermitApplicationView(GeneratedPermitApplicationView):
    """GET/PATCH a Permit Application and its nested tiles.

    The update that first sets the submission date is the submission: it assigns
    the application id and attaches the requirement working copies.
    """

    def get_queryset(self):
        """Own filings plus the company's, matching what the dashboard lists.
        Replaces UserOwnedResourceMixin's creator-only filter rather than adding
        to it, which would 404 a colleague opening what their company tab shows.
        """
        return ArchesModelAPIMixin.get_queryset(self).filter(
            OrganizationService().visible_to(self.request.user, PA.OWNING_ORGANIZATION)
        )

    def update(self, request, *args, **kwargs):
        block_organization(
            request,
            PermitApplicationGroupAliases.APPLICATION_IDENTIFICATION,
            PA.OWNING_ORGANIZATION,
        )
        return PermitApplicationService(request).submit(
            self.get_object(),
            request.data,
            save=lambda: super(PermitApplicationView, self).update(
                request, *args, **kwargs
            ),
        )


@extend_schema(tags=["External: permit_application"])
class PermitApplicationCreateView(GeneratedPermitApplicationListView):
    """POST a new Permit Application, seeding its application id. A body that
    already carries the submission date attaches the requirement working copies
    here; one saved as a draft gets them on the update that submits it (see the
    detail view)."""

    # Applicants file their own applications, so this only asks for a login; the
    # owning organization stamped on create is what scopes who reads it back.
    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "options"]

    def create(self, request, *args, **kwargs):
        stamp_organization(
            request,
            PermitApplicationGroupAliases.APPLICATION_IDENTIFICATION,
            PA.OWNING_ORGANIZATION,
        )
        return PermitApplicationService(request).create(
            request.data,
            save=lambda: super(PermitApplicationCreateView, self).create(
                request, *args, **kwargs
            ),
        )
