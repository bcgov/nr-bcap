"""Permit Application CRUD: the generated owner-scoped views plus the business
rules that don't belong in codegen -- seed the application id on create, and
attach the requirement working copies on first submission.

These subclass the generated views and are registered (in
bcap.urls_api_documented) at the same paths as the generated routes, declared
first, so they shadow them.
"""

from drf_spectacular.utils import extend_schema

from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin

from bcap.permissions.route_permissions import SubmitterOrInternal
from bcap.permissions.permit_resource_access import PermitResourceAccess
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
    """GET/PATCH a Permit Application and its nested tiles, for the applicant
    filing it as much as for the staff reviewing it.

    The update that first sets the submission date is the submission: it assigns
    the application id and attaches the requirement working copies.
    """

    permission_classes = [SubmitterOrInternal]

    def get_queryset(self):
        """What the caller may open. Replaces UserOwnedResourceMixin's
        creator-only filter rather than adding to it, which would 404 both a
        colleague opening what their company tab shows and staff opening any
        filing at all."""
        return ArchesModelAPIMixin.get_queryset(self).filter(
            PermitResourceAccess.visible_permits_for_organization_or_user_or_staff(
                self.request.user
            )
        )

    def get_object(self, permission_callable=None, **kwargs):
        """Dropping the callable takes the graph policy out of the read: an
        applicant holds no grant on the graph, so it would refuse a colleague
        the filing their company tab just listed."""
        permit = super().get_object(**kwargs)
        PermitResourceAccess.require_view(self.request.user, permit.pk)
        return permit

    def update(self, request, *args, **kwargs):
        PermitResourceAccess.require_change(request.user, self.kwargs["pk"])
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
    permission_classes = [SubmitterOrInternal]
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
