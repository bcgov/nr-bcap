from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from arches.app.views.file import FileView
from bcap.views.api import (
    BCAPResourceDetailView,
    BordenNumber,
    BordenNumberExternal,
    MVT,
    LegislativeAct,
    RegisterType,
    RelatedSiteVisits,
    ControlledListHierarchy,
    TranslatableResourceTypesView,
    TranslateToResourceTypeView,
    RequirementSubmission,
)
from bcap.views.registration_link_api import RegistrationClaimView
from bcap.urls_api_documented import api_documented_patterns
from bcap.views.auth import auth_callback
from bcap.views.resource import ResourceReportView, ResourceEditLogView
from bcap.views.search import export_results
from bcgov_arches_common.views.map import BCTileserverProxyView
from rest_framework.permissions import IsAdminUser
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

uuid_regex = settings.UUID_REGEX

bcap_patterns = [
    # Override the library's OAuth callback (before its include below) so an
    # invited user's account is created on first sign-in.
    path("auth/eoauth_cb", auth_callback, name="auth_callback"),
    path(
        "files/<uuid:fileid>",
        FileView.as_view(),
        name="files",
    ),
    path(
        "bctileserver/",
        BCTileserverProxyView.as_view(),
        name="bcap_tile_server_root",
    ),
    path(
        "bctileserver/<path:path>",
        BCTileserverProxyView.as_view(),
        name="bcap_tile_server",
    ),
    path(
        "borden_number/<uuid:resourceinstanceid>",
        BordenNumber.as_view(),
        name="borden_number",
    ),
    # Used by BCRHP to get & reserve a borden number
    path(
        "api/borden-number/",
        BordenNumberExternal.as_view(),
        name="borden-number-external",
    ),
    path(
        "register_type/<uuid:resourceinstanceid>",
        RegisterType.as_view(),
        name="register_type",
    ),
    path(
        "legislative_act/<uuid:act_id>",
        LegislativeAct.as_view(),
        name="legislative_act",
    ),
    path(
        "api/hierarchy/<uuid:list_item_id>/",
        ControlledListHierarchy.as_view(),
        name="controlled_list_hierarchy",
    ),
    # Documented API surface (hand-written + generated graph views). Splatted
    # prefix-free so the single PREFIX wrap below applies here too, and ordering
    # vs the api-resource override further down is preserved.
    *api_documented_patterns,
    # MVT requires regex due to literal {z}, {x}, {y} placeholders
    re_path(
        r"^mvt/(?P<nodeid>%s)/(?P<zoom>[0-9]+|\{z\})/(?P<x>[0-9]+|\{x\})/(?P<y>[0-9]+|\{y\}).pbf$"
        % uuid_regex,
        MVT.as_view(),
        name="mvt",
    ),
    path(
        "report/<uuid:resourceid>",
        ResourceReportView.as_view(),
        name="resource_report",
    ),
    path(
        "resource/history",
        ResourceEditLogView.as_view(),
        name="edit_history",
    ),
    path(
        "api/arch_site_related_resources/<slug:graph>/<uuid:pk>",
        RelatedSiteVisits.as_view(),
        name="api-related-site-resources",
    ),
    path(
        "api/arch_site_related_resources/<slug:graph>",
        RelatedSiteVisits.as_view(),
        name="api-related-sites-resources",
    ),
    path(
        "api/translate-to-resource-type",
        TranslateToResourceTypeView.as_view(),
        name="translate_to_resource_type",
    ),
    path(
        "api/requirement_submissions/<uuid:resource_id>",
        RequirementSubmission.as_view(),
        name="requirement_submission",
    ),
    path(
        "api/translatable-resource-types",
        TranslatableResourceTypesView.as_view(),
        name="translatable_resource_types",
    ),
    path("search/export_results", export_results, name="export_results"),
    # Signup-link target: bounces the visitor through BCSC, BCEID or IDIR
    # login, where the token (stashed in the session) is redeemed.
    # Anonymous-reachable, so it is added to auth_exempt_pages in settings.
    path(
        "signup/claim",
        RegistrationClaimView.as_view(),
        name="registration_claim",
    ),
    path(
        "api/schema",
        SpectacularAPIView.as_view(permission_classes=[IsAdminUser]),
        name="schema",
    ),
    path(
        "api/schema/swagger-ui",
        SpectacularSwaggerView.as_view(
            url_name="schema", permission_classes=[IsAdminUser]
        ),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc",
        SpectacularRedocView.as_view(
            url_name="schema", permission_classes=[IsAdminUser]
        ),
        name="redoc",
    ),
    # Override arches_querysets' resource detail route so the response is
    # post-processed to inject MVTTiler-configured attrs into geojson
    # feature properties. Must precede the arches_querysets include.
    path(
        "api/resource/<slug:graph>/<uuid:pk>",
        BCAPResourceDetailView.as_view(),
        name="api-resource",
    ),
    path("", include("bcgov_arches_common.urls")),
    path("", include("arches_controlled_lists.urls")),
    path("", include("arches_component_lab.urls")),
    path("", include("arches_querysets.urls")),
    path("", include("arches.urls")),
]


urlpatterns = [
    path(settings.URL_PREFIX, include(bcap_patterns)),
]

handler400 = "arches.app.views.main.custom_400"
handler403 = "arches.app.views.main.custom_403"
handler404 = "arches.app.views.main.custom_404"
handler500 = "arches.app.views.main.custom_500"

# Only handle i18n routing in active project. This will still handle the routes provided by Arches core and Arches applications,
# but handling i18n routes in multiple places causes application errors.
if settings.ROOT_URLCONF == __name__:
    if settings.SHOW_LANGUAGE_SWITCH is True:
        urlpatterns = i18n_patterns(*urlpatterns)

    urlpatterns.append(path("i18n/", include("django.conf.urls.i18n")))
