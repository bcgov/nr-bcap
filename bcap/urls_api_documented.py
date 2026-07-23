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

from bcap.views.dashboard_api import (
    InternalDashboardView,
    ExternalDashboardView,
)
from bcap.views.workflow_draft_api import (
    WorkflowDraftListCreateView,
    WorkflowDraftDetailView,
)
from bcap.views.permit_application_api import (
    PermitApplicationView,
    PermitApplicationCreateView,
)
from bcap.views.process_requirement_api import (
    ModuleRequirementsView,
    ModuleRequirementView,
    RequirementChecklistView,
    RequirementStatusView,
    PermitModuleView,
    ProcessRequirementListView,
    ProcessRequirementSeedView,
    ProcessRequirementView,
)
from bcap.views.bcap_message_api import (
    BcapMessageContributorsView,
    BcapMessageCreateView,
    BcapMessageDetailView,
    BcapMessageThreadsView,
    BcapMessageThreadView,
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
        "api/workflow_draft/<slug:graph_slug>",
        WorkflowDraftListCreateView.as_view(),
        name="workflow_draft_list_create",
    ),
    # Submitter - object level user filtering
    path(
        "api/workflow_draft/<slug:graph_slug>/<uuid:pk>",
        WorkflowDraftDetailView.as_view(),
        name="workflow_draft_detail",
    ),
    # Submitter - object level user filtering - override
    path(
        "api/permit_application",
        PermitApplicationCreateView.as_view(),
        name="permit_application_create",
    ),
    # External - object level user filtering - override.
    path(
        "api/permit_application/<uuid:pk>/",
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
    # Seed the per-type process requirements onto a permit application; the
    # permit type (inspection / investigation / alteration) is a path segment.
    path(
        "api/permit_application/<uuid:pk>/process_requirement/<slug:permit_type>",
        ProcessRequirementSeedView.as_view(),
        name="seed_process_requirements",
    ),
    # Remove a submitted module (its process_module tile) from a permit.
    path(
        "api/permit_application/<uuid:pk>/module/<uuid:module_tileid>",
        PermitModuleView.as_view(),
        name="permit_module",
    ),
    # Reorder a module's process requirements.
    path(
        "api/permit_application/<uuid:pk>/module/<uuid:module_tileid>/requirements",
        ModuleRequirementsView.as_view(),
        name="module_requirements",
    ),
    # Remove one process requirement from a module.
    path(
        "api/permit_application/<uuid:pk>/module/<uuid:module_tileid>"
        "/requirement/<uuid:requirement_id>",
        ModuleRequirementView.as_view(),
        name="module_requirement",
    ),
    # Save a process requirement's checklist (name + ordered steps).
    path(
        "api/process_requirement/<uuid:requirement_id>/checklist",
        RequirementChecklistView.as_view(),
        name="requirement_checklist",
    ),
    # Mark a non-checklist process requirement satisfied/unsatisfied.
    path(
        "api/process_requirement/<uuid:requirement_id>/status",
        RequirementStatusView.as_view(),
        name="requirement_status",
    ),
    path(
        "api/bcap_message/resource/<uuid:resource_id>/threads",
        BcapMessageThreadsView.as_view(),
        name="bcap_message_resource_threads",
    ),
    path(
        "api/bcap_message/resource/<uuid:resource_id>/contributor",
        BcapMessageContributorsView.as_view(),
        name="bcap_message_resource_contributors",
    ),
    path(
        "api/bcap_message/thread/<uuid:thread_id>/messages",
        BcapMessageThreadView.as_view(),
        name="bcap_message_thread_messages",
    ),
    # Override so we can link/verify.
    path(
        "api/bcap_message",
        BcapMessageCreateView.as_view(),
        name="bcap_message_list_create",
    ),
    # Override the generated detail route: GET + PATCH gated on the
    # resource_context (not owner-scoped). PATCH is locked to the read state.
    path(
        "api/bcap_message/<uuid:pk>/",
        BcapMessageDetailView.as_view(),
        name="bcap_message_detail",
    ),
]

# Override the generated
api_documented_patterns = [
    *documented_api_patterns,
    path("", include("bcap.urls_api_generated")),
]

urlpatterns = [path(settings.URL_PREFIX, include(api_documented_patterns))]
