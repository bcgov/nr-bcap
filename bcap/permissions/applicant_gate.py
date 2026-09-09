"""Middleware keeping applicants off the arches ecosystem's own routes.

Installed in MIDDLEWARE. The permission framework governs the views that ask
it; this governs the ones that don't, which is most of them.
"""

import logging

from django.core.exceptions import PermissionDenied

from bcap.permissions.groups import is_internal_user
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import graph_slugs_of, relatable_graph_slugs

logger = logging.getLogger(__name__)


class ArchesDefaultDenyApplicantGate:
    """The arches ecosystem is staff-only for applicants, bar the views the
    permit app needs. An applicant's grant is graph-wide until an instance
    narrows it, so a view answering from nodegroup permissions alone hands out
    everyone's, and some routes take an id and check nothing. Listing what is
    allowed means a view added upstream is refused until someone decides
    otherwise, and matching on the module rather than the URL survives a route
    being renamed or moved.

    Every package is governed, not just arches core, since they carry the same
    permissive reads. BCAP's own routes answer for themselves.
    """

    GOVERNED_PACKAGES = (
        "arches.",
        "arches_querysets.",
        "arches_controlled_lists.",
        "arches_vue_components.",
        "bcgov_arches_common.",
    )
    # Taken from what the permit app was seen to call, not from guesswork.
    # A missing entry shows up as a denial in the log rather than as a mystery,
    # so add what turns up there instead of widening this on spec.
    APPLICANT_ALLOWED = (
        "arches.app.views.api.i18n",
        "arches.app.views.api.user",
        "arches.app.views.auth",
        "arches.app.views.file",
        "arches.app.views.main",
        "arches.app.views.notifications",
        "arches.app.views.plugin",
        "arches.app.views.user",
        "arches_controlled_lists.views",
        "arches_vue_components.views.api.card_x_node_x_widget",
        "arches_vue_components.views.api.concept",
        "arches_vue_components.views.api.language",
        "arches_vue_components.views.api.map",
        "bcgov_arches_common.views.api.map",
        "bcgov_arches_common.views.auth",
        "bcgov_arches_common.views.map",
    )

    # The picker behind resource-instance widgets lists every instance of the
    # graphs a node names, and takes that node from the URL, so an applicant
    # could read any graph's descriptors through it. They get the nodes that
    # offer contributors and nothing else, which is what their forms pick: an
    # archaeologist, a proponent, an organization. Read from the node rather
    # than listed here, so editing a graph cannot widen it by surprise.
    #
    # arches-vue-components should check the page of candidates it is about to
    # return, one user_can_read_resource each. Belongs upstream.
    PICKER_VIEW = "arches_vue_components.views.api.relatable_resources"
    PICKER_GRAPHS = frozenset({GraphSlugs.CONTRIBUTOR})

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        module = view_func.__module__
        if not module.startswith(self.GOVERNED_PACKAGES):
            return None
        if is_internal_user(request.user):
            return None
        if module.startswith(self.PICKER_VIEW):
            offered = relatable_graph_slugs(
                view_kwargs["graph"], view_kwargs["node_alias"]
            )
            # An initialValue is echoed back with its descriptor whatever graph
            # it names, so it clears the same bar the candidates do.
            named = offered | graph_slugs_of(request.GET.getlist("initialValue"))
            if offered and named <= self.PICKER_GRAPHS:
                logger.info(
                    "Applicant allowed %s, a picker of %s",
                    request.path,
                    sorted(named),
                )
                return None
        if module.startswith(self.APPLICANT_ALLOWED):
            logger.info("Applicant allowed %s, served by %s", request.path, module)
            return None
        logger.warning("Applicant denied %s, served by %s", request.path, module)
        raise PermissionDenied
