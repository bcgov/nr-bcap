from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from arches.app.views.file import FileView
from bcap.views.api import (
    BordenNumber,
    BordenNumberExternal,
    MVT,
    LegislativeAct,
    UserProfile,
    RelatedSiteVisits,
    ControlledListHierarchy,
    TranslatableResourceTypesView,
    TranslateToResourceTypeView,
)
from bcap.views.resource import ResourceReportView, ResourceEditLogView
from bcgov_arches_common.views.map import BCTileserverProxyView

uuid_regex = settings.UUID_REGEX

PREFIX = (
    settings.BCGOV_PROXY_PREFIX.rstrip("/") + "/" if settings.BCGOV_PROXY_PREFIX else ""
)


urlpatterns = [
    path(
        f"{PREFIX}localfiles/<uuid:fileid>",
        FileView.as_view(),
        name="localfiles",
    ),
    path(
        f"{PREFIX}bctileserver/<path:path>",
        BCTileserverProxyView.as_view(),
        name="bcap_tile_server",
    ),
    path(
        f"{PREFIX}borden_number/<uuid:resourceinstanceid>",
        BordenNumber.as_view(),
        name="borden_number",
    ),
    # Used by BCRHP to get & reserve a borden number
    path(
        f"{PREFIX}api/borden-number/",
        BordenNumberExternal.as_view(),
        name="borden-number-external",
    ),
    path(
        f"{PREFIX}legislative_act/<uuid:act_id>",
        LegislativeAct.as_view(),
        name="legislative_act",
    ),
    path(
        f"{PREFIX}api/hierarchy/<uuid:list_item_id>/",
        ControlledListHierarchy.as_view(),
        name="controlled_list_hierarchy",
    ),
    path(
        f"{PREFIX}user_profile",
        UserProfile.as_view(),
        name="user_profile",
    ),
    # MVT requires regex due to literal {z}, {x}, {y} placeholders
    re_path(
        rf"^{PREFIX}"
        + r"mvt/(?P<nodeid>%s)/(?P<zoom>[0-9]+|\{z\})/(?P<x>[0-9]+|\{x\})/(?P<y>[0-9]+|\{y\}).pbf$"
        % uuid_regex,
        MVT.as_view(),
        name="mvt",
    ),
    path(
        f"{PREFIX}report/<uuid:resourceid>",
        ResourceReportView.as_view(),
        name="resource_report",
    ),
    path(
        f"{PREFIX}resource/history",
        ResourceEditLogView.as_view(),
        name="edit_history",
    ),
    path(
        f"{PREFIX}api/arch_site_related_resources/<slug:graph>/<uuid:pk>",
        RelatedSiteVisits.as_view(),
        name="api-related-site-resources",
    ),
    path(
        f"{PREFIX}api/arch_site_related_resources/<slug:graph>",
        RelatedSiteVisits.as_view(),
        name="api-related-sites-resources",
    ),
    path(
        f"{PREFIX}api/translate-to-resource-type",
        TranslateToResourceTypeView.as_view(),
        name="translate_to_resource_type",
    ),
    path(
        f"{PREFIX}api/translatable-resource-types",
        TranslatableResourceTypesView.as_view(),
        name="translatable_resource_types",
    ),
    path(f"{PREFIX}", include("bcgov_arches_common.urls")),
    path(f"{PREFIX}", include("arches_controlled_lists.urls")),
    path(f"{PREFIX}", include("arches_component_lab.urls")),
    path(f"{PREFIX}", include("arches_querysets.urls")),
    path(f"{PREFIX}", include("arches.urls")),
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
