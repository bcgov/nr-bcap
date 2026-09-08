"""Default-deny framework, installed as PERMISSION_FRAMEWORK so every arches
path touching resources runs through it, and the route gates that decide who may
reach an endpoint in the first place. Who may reach what is PERMISSION_DEFAULTS
in permission_settings.py; object ownership is enforced separately again, by the
user-owned queryset filter.

An instance check arrives here from a route: a view asks the arches permission
backend, which dispatches to this class. The stock policy answers first, then
an applicant's answer is narrowed by the permit reach check in
permit_resource_access. That module also holds the helpers views call directly,
and those do ask the policy, so the narrowing here must use the reach check
rather than a helper or it would arrive back at this method and recurse.
"""

import logging

from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from rest_framework import permissions

from arches.app.permissions.arches_default_deny import (
    ArchesDefaultDenyPermissionFramework,
)
from arches.app.utils.decorators import group_required as group_required_decorator
from arches.app.utils.permission_backend import group_required

from bcap.permissions.groups import Groups, group_id, is_internal_user
from bcap.permissions.permission_settings import PERMIT_SCOPED_GRAPHS
from bcap.permissions.permit_resource_access import PermitResourceAccess
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import graph_slugs_of, relatable_graph_slugs

ANONYMOUS_USERNAME = "anonymous"

logger = logging.getLogger(__name__)


class BcapArchesPermissionFramework(ArchesDefaultDenyPermissionFramework):
    def check_resource_instance_permissions(
        self, user, resourceid, permission, *, resource=None
    ):
        """The graph policy grants an applicant a whole graph; narrow that to
        the instances their own permits reach. Only graphs a permit points at
        are narrowed, since anything else finds no permit and is denied."""
        result = super().check_resource_instance_permissions(
            user, resourceid, permission, resource=resource
        )
        if (
            result.get("permitted")
            and not is_internal_user(user)
            and str(result["resource"].graph_id) in PERMIT_SCOPED_GRAPHS
        ):
            result["permitted"] = PermitResourceAccess.on_visible_permit_or_draft(
                user, result["resource"].pk
            )
        return result

    def get_index_values(self, resource, **kwargs):
        """Keep the applicant grant out of the search index. The index matches
        on group id alone, with no room for the check above, so leaving
        Submitter on it would show every applicant every other's permits.

        TODO: in the future it might be possible to expand this to owning organizations,
        but I think we're hiding the search for submitters for now."""
        values = super().get_index_values(resource, **kwargs)
        submitter_id = group_id(Groups.SUBMITTER)
        for key in ("groups_read", "groups_edit"):
            values[key] = [gid for gid in values[key] if gid != submitter_id]
        return values

    def user_is_resource_reviewer(self, user):
        """Signed-in users author for real; the public user keeps the stock
        check. A non-reviewer's tile save lands in provisionaledits with the
        tile written empty, and BCAP has no approval step, so narrowing this to
        a role loses that role's edits silently rather than refusing them.

        TODO: arches gates the lifecycle-state POST on this call alone, with no
        ownership check after it, so an applicant can change any resource's
        state by id. Shadow that route ahead of the arches include.
        In the future we want to make this resource based,
        but I'm not sure if it's possible to do this way.
        """
        if user.is_authenticated and user.username != ANONYMOUS_USERNAME:
            return True
        return super().user_is_resource_reviewer(user)


# Route guards: which role may reach an endpoint at all, before the framework
# above is asked about any one resource.


def any_groups_required(*group_names):
    """A DRF permission passing if the user is in any of the named groups."""

    class _RolesRequired(permissions.BasePermission):
        def has_permission(self, request, view):
            return bool(group_required(request.user, *group_names))

    return _RolesRequired


def any_groups_required_django_view(*group_names, raise_exception=False):
    """Class decorator for plain Django views, which ignore permission_classes.
    Without raise_exception a denied user is redirected to login rather than
    given a 403, which suits browser pages but not JSON endpoints."""
    return method_decorator(
        group_required_decorator(*group_names, raise_exception=raise_exception),
        name="dispatch",
    )


class SubmitterReadsInternalReadWrites(permissions.BasePermission):
    """Applicants read, staff read and write. Both halves are stated as
    positive grants: under default deny an applicant's lack of write access
    needs no permission of its own, and a negative one could contradict a
    positive one the same user holds."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(
                group_required(
                    request.user, Groups.SUBMITTER, Groups.ARCHAEOLOGY_BRANCH
                )
            )
        return bool(group_required(request.user, Groups.ARCHAEOLOGY_BRANCH))


Submitter = any_groups_required(Groups.SUBMITTER)
Internal = any_groups_required(Groups.ARCHAEOLOGY_BRANCH)
SubmitterOrInternal = any_groups_required(Groups.SUBMITTER, Groups.ARCHAEOLOGY_BRANCH)

internal_only_django_view = any_groups_required_django_view(
    Groups.ARCHAEOLOGY_BRANCH, raise_exception=True
)
resource_editor_only_django_view = any_groups_required_django_view(
    Groups.RESOURCE_EDITOR
)
resource_exporter_only_function_view = group_required_decorator(
    Groups.RESOURCE_EXPORTER
)


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
