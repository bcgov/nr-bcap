"""Permit Application CRUD: the generated owner-scoped views plus the business
rules that don't belong in codegen -- seed the application id on create, and
attach the requirement working copies on first submission.

These subclass the generated views and are registered (in
bcap.urls_api_documented) at the same paths as the generated routes, declared
first, so they shadow them.
"""

from drf_spectacular.utils import extend_schema

from arches_querysets.rest_framework.permissions import ResourceEditor

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

    # Partial edits only: a PUT resets every node the body leaves out, the owning
    # organization an applicant may not set included. The generated base still
    # carries a put handler, so blocking it here is what makes it a 405.
    http_method_names = ["get", "patch", "head", "options"]

    def update(self, request, *args, **kwargs):
        block_organization(
            request,
            PermitApplicationGroupAliases.APPLICATION_IDENTIFICATION,
            PA.OWNING_ORGANIZATION,
        )
        return PermitApplicationService().submit(
            self.get_object(),
            request.data,
            save=lambda: super(PermitApplicationView, self).update(
                request, *args, **kwargs
            ),
        )


@extend_schema(tags=["External: permit_application"])
class PermitApplicationCreateView(GeneratedPermitApplicationListView):
    """POST a new Permit Application, seeding its application id.

    Create-only (POST); the requirements are attached later, on submission (see
    the detail view).
    """

    permission_classes = [ResourceEditor]
    http_method_names = ["post", "options"]

    def create(self, request, *args, **kwargs):
        stamp_organization(
            request,
            PermitApplicationGroupAliases.APPLICATION_IDENTIFICATION,
            PA.OWNING_ORGANIZATION,
        )
        return PermitApplicationService().create(
            request.data,
            save=lambda: super(PermitApplicationCreateView, self).create(
                request, *args, **kwargs
            ),
        )
