"""Object-level access for external applicants.

The route gates in route_permissions say which role may call an endpoint; this
says which instances an external caller may touch once inside one. An applicant
reaches what they created, plus anything hanging off a permit application they
can see: its process requirements and the submission hosts under them. Internal
staff are settled by their route gate, so they pass.

The company-visibility filters live here too, so the lists (the dashboard, the
draft list) and the per-instance checks answer "my work, and my company's" from
one place instead of each assembling the rule themselves.
"""

from rest_framework.exceptions import PermissionDenied

from arches.app.models.models import ResourceXResource
from arches.app.utils.permission_backend import user_can_edit_resource

from arches_querysets.models import ResourceTileTree

from bcap.permissions.groups import is_internal_user
from bcap.services.contributor.organization_service import OrganizationService
from bcap.services.dashboard.base_graph_service import BaseGraphService
from bcap.util.aliases.permit_application import PermitApplicationAliases
from bcap.util.aliases.workflow_drafts import WorkflowDraftsAliases
from bcap.util.bcap_aliases import GraphSlugs


class PermitResourceAccess(BaseGraphService):
    """Whether a user may touch one resource instance, and the matching filters
    for listing what they may touch."""

    PERMIT_ORG = PermitApplicationAliases.OWNING_ORGANIZATION
    DRAFT_ORG = WorkflowDraftsAliases.OWNING_ORGANIZATION

    @classmethod
    def visible_permits_for_organization_or_user(cls, user):
        """Permit applications this user may see: their own filed under no
        company, plus anything filed under a company they belong to."""
        return OrganizationService().visible_with_organization_or_user(
            user, cls.PERMIT_ORG
        )

    @classmethod
    def visible_drafts_for_organization_or_user(cls, user):
        """Drafts this user may see, by the same rule as their permits."""
        return OrganizationService().visible_with_organization_or_user(
            user, cls.DRAFT_ORG
        )

    @classmethod
    def can_view(cls, user, resource_id):
        if not resource_id:
            return False
        if is_internal_user(user):
            return True
        if cls._own_or_company_permit_exists(
            user, cls._candidate_permit_ids(resource_id)
        ):
            return True
        return cls._own_or_company_draft_exists(user, resource_id)

    @classmethod
    def can_change(cls, user, resource_id):
        """Same reachability, but staff must also hold the graph policy's edit
        grant: a read-only role sees a permit without being able to act on it."""
        if is_internal_user(user):
            return bool(resource_id) and user_can_edit_resource(
                user, resourceid=resource_id
            )
        return cls.can_view(user, resource_id)

    @classmethod
    def require_view(cls, user, resource_id):
        """Raise 403 unless the user may reach this resource instance."""
        if not cls.can_view(user, resource_id):
            raise PermissionDenied("No access to this resource.")

    @classmethod
    def require_change(cls, user, resource_id):
        """Raise 403 unless the user may act on this resource instance."""
        if not cls.can_change(user, resource_id):
            raise PermissionDenied("No access to this resource.")

    @classmethod
    def _own_or_company_draft_exists(cls, user, resource_id):
        """A draft hangs off no permit, so it answers for itself, by the rule the
        draft list already applies."""
        return (
            ResourceTileTree.get_tiles(GraphSlugs.WORKFLOW_DRAFTS)
            .filter(cls.visible_drafts_for_organization_or_user(user), pk=resource_id)
            .exists()
        )

    @classmethod
    def _candidate_permit_ids(cls, resource_id):
        """The chain a resource can hang off a permit by: permit -> requirement
        -> submission host, walked back up. Only these two hops, so a resource
        shared with other applicants (a contributor, an organization) never
        bridges into their permits."""
        requirements = {str(resource_id)} | cls._referencing(str(resource_id))
        return requirements | cls._referencing(*requirements)

    @staticmethod
    def _referencing(*resource_ids):
        """The resources pointing at these, from the reference table arches
        maintains on tile save."""
        return {
            str(from_id)
            for from_id in ResourceXResource.objects.filter(
                to_resource_id__in=resource_ids
            ).values_list("from_resource_id", flat=True)
        }

    @classmethod
    def _own_or_company_permit_exists(cls, user, resource_ids):
        """Whether any of these ids is a permit application this user may see:
        one they created under no organization, or one filed under an
        organization they belong to."""
        return (
            ResourceTileTree.get_tiles(
                GraphSlugs.PERMIT_APPLICATION,
                nodes=cls.nodes(GraphSlugs.PERMIT_APPLICATION, [cls.PERMIT_ORG]),
                resource_ids=list(resource_ids),
            )
            .filter(cls.visible_permits_for_organization_or_user(user))
            .exists()
        )
