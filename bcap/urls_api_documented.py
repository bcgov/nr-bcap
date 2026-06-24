"""The public OpenAPI surface for drf_spectacular.

Defines the documented bcap routes and exposes them as a standalone, prefixed
urlconf so the schema covers only the bcap API, not all of Arches. Used both for
codegen and as SERVE_URLCONF (the served /api/schema):

    python manage.py spectacular --urlconf bcap.urls_api_documented --file schema.yml

bcap.urls imports ``api_documented_patterns`` from here and serves it (prefixed)
alongside the rest of the app.
"""

from django.urls import include, path
from django.conf import settings

from bcap.views.dashboard_api import InternalDashboardView, ExternalDashboardView
from bcap.views.resource_draft_api import (
    ResourceDraftListCreateView,
    ResourceDraftDetailView,
)
from bcap.views.permit_application_api import (
    PermitApplicationView,
    PermitApplicationCreateView,
)
from bcap.views.process_requirement_api import (
    ProcessRequirementListView,
    ProcessRequirementView,
)
from bcap.views.user_api import UserProfile
from bcap.views.registration_link_api import (
    AssignableGroupsView,
    RegistrationLinkView,
    UnlinkedContributorsView,
)

# Hand-written routes that belong in the OpenAPI schema. Declared WITHOUT the
# proxy prefix; the prefix is applied once at each urlconf entrypoint (here for
# the schema, and in bcap.urls for the served app).
documented_api_patterns = [
    path("user_profile", UserProfile.as_view(), name="user_profile"),
    path(
        "api/dashboard/internal",
        InternalDashboardView.as_view(),
        name="dashboard_internal",
    ),
    path(
        "api/dashboard/external",
        ExternalDashboardView.as_view(),
        name="dashboard_external",
    ),
    # Submitter - object level user filtering
    path(
        "api/resource_draft/<slug:graph_slug>",
        ResourceDraftListCreateView.as_view(),
        name="resource_draft_list_create",
    ),
    # Submitter - object level user filtering
    path(
        "api/resource_draft/<slug:graph_slug>/<uuid:pk>",
        ResourceDraftDetailView.as_view(),
        name="resource_draft_detail",
    ),
    # Submitter - object level user filtering - override
    path(
        "api/resource/permit_application",
        PermitApplicationCreateView.as_view(),
        name="permit_application_create",
    ),
    # External - object level user filtering - override - well need this for next PR override PUT / PATCH
    path(
        "api/resource/permit_application/<uuid:pk>",
        PermitApplicationView.as_view(),
        name="api_permit_application",
    ),
    # Admin - issue a signup link and list invitable Contributors
    path(
        "api/registration_link",
        RegistrationLinkView.as_view(),
        name="registration_link",
    ),
    path(
        "api/contributors/unlinked",
        UnlinkedContributorsView.as_view(),
        name="unlinked_contributors",
    ),
    path(
        "api/assignable_groups",
        AssignableGroupsView.as_view(),
        name="assignable_groups",
    ),
    # Override the generated owner-scoped process_requirement routes so
    # superusers and Resource Editors can read any instance. Declared before the
    # generated include below, so these win for incoming requests.
    path(
        "api/process_requirement",
        ProcessRequirementListView.as_view(),
        name="api_process_requirement_list",
    ),
    path(
        "api/process_requirement/<uuid:pk>/",
        ProcessRequirementView.as_view(),
        name="api_process_requirement",
    ),
]

# Override the generated
api_documented_patterns = [
    *documented_api_patterns,
    path("", include("bcap.urls_api_generated")),
]

urlpatterns = [path(settings.URL_PREFIX, include(api_documented_patterns))]
