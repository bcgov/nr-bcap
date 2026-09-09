"""Object-level access for external applicants: which instances a caller may
touch, once their route gate has let them in.

An applicant reaches a permit application their company holds, or that they
filed under no company, and whatever hangs off one within two hops. Authorship
is not enough on its own and is deliberately taken back: arches permits a
resource's creator before it consults any grant, and the framework narrows that
away with the check here. The reach rules live here too -- the organization
filters and the ids an applicant reaches -- so each service builds its own base
query from the same answer to "my work, and my company's".
"""

import logging

from rest_framework.exceptions import PermissionDenied

from arches.app.models.models import ResourceXResource
from arches.app.utils.permission_backend import (
    user_can_edit_resource,
    user_can_read_resource,
)

from arches_querysets.models import ResourceTileTree

from bcap.util.graph import nodes_for
from bcap.services.contributor.organization_service import OrganizationService
from bcap.util.aliases.permit_application import PermitApplicationAliases
from bcap.util.aliases.workflow_drafts import WorkflowDraftsAliases
from bcap.util.bcap_aliases import GraphSlugs

logger = logging.getLogger(__name__)


class PermitAccess:
    """Whether a user may touch one resource instance, and the matching filters
    for listing what they may touch."""

    PERMIT_ORG = PermitApplicationAliases.OWNING_ORGANIZATION
    DRAFT_ORG = WorkflowDraftsAliases.OWNING_ORGANIZATION

    @classmethod
    def own_or_company_permits(cls, user):
        """Their own filed under no company, plus anything filed under a company
        they belong to."""
        return OrganizationService().visible_with_organization_or_user(
            user, cls.PERMIT_ORG
        )

    @classmethod
    def own_or_company_drafts(cls, user):
        """By the same rule as their permits."""
        return OrganizationService().visible_with_organization_or_user(
            user, cls.DRAFT_ORG
        )

    @classmethod
    def own_or_company_resource_ids(cls, user):
        """Every resource id an applicant may open: their own and their company's
        permits, and what hangs off one within two hops (a requirement, its
        submission host). The list-shaped twin of the reach check below."""
        permits = {
            str(pk) for pk in cls._visible_permits(user).values_list("pk", flat=True)
        }
        requirements = cls._referenced_by(permits)
        return permits | requirements | cls._referenced_by(requirements)

    @classmethod
    def _visible_permits(cls, user, resource_ids=None):
        """The permits this user may see, carrying just the organization node the
        rule reads."""
        return ResourceTileTree.get_tiles(
            GraphSlugs.PERMIT_APPLICATION,
            nodes=nodes_for(GraphSlugs.PERMIT_APPLICATION, [cls.PERMIT_ORG]),
            resource_ids=resource_ids,
        ).filter(cls.own_or_company_permits(user))

    @staticmethod
    def _referenced_by(resource_ids):
        """The resources these point at, from the reference table arches maintains
        on tile save. The inverse of the walk up to a permit."""
        if not resource_ids:
            return set()
        return {
            str(to_id)
            for to_id in ResourceXResource.objects.filter(
                from_resource_id__in=resource_ids
            ).values_list("to_resource_id", flat=True)
        }

    @classmethod
    def on_visible_permit_or_draft(cls, user, resource_id):
        """Whether this resource hangs off a permit application or draft the
        user can see, by the same own-or-company rule the list filters apply.
        Asks nothing of the graph policy, so the permission framework can narrow
        an applicant's graph grant with it without looping back through itself."""
        if not resource_id:
            return False
        if cls._own_or_company_permit_exists(
            user, cls._candidate_permit_ids(resource_id)
        ):
            return True
        return cls._own_or_company_draft_exists(user, resource_id)

    @classmethod
    def can_view(cls, user, resource_id):
        """One question for staff and applicants alike: the graph policy, which
        the permission framework narrows for an applicant by calling back into
        the reach check above. Without an id arches answers the model-level
        question instead, which grants rather than denies, so guard it."""
        return bool(resource_id) and user_can_read_resource(
            user, resourceid=resource_id
        )

    @classmethod
    def can_change(cls, user, resource_id):
        """As the read, against the edit grant."""
        return bool(resource_id) and user_can_edit_resource(
            user, resourceid=resource_id
        )

    @classmethod
    def require_view(cls, user, resource_id):
        """Raise 403 unless the user may reach this resource instance. Logged by
        id, since a username is a credential."""
        if not cls.can_view(user, resource_id):
            logger.warning("User %s denied read of resource %s", user.id, resource_id)
            raise PermissionDenied("No access to this resource.")

    @classmethod
    def require_change(cls, user, resource_id):
        """Raise 403 unless the user may act on this resource instance."""
        if not cls.can_change(user, resource_id):
            logger.warning("User %s denied edit of resource %s", user.id, resource_id)
            raise PermissionDenied("No access to this resource.")

    @classmethod
    def _own_or_company_draft_exists(cls, user, resource_id):
        """A draft hangs off no permit, so it answers for itself, by the rule the
        draft list already applies."""
        return (
            ResourceTileTree.get_tiles(GraphSlugs.WORKFLOW_DRAFTS)
            .filter(cls.own_or_company_drafts(user), pk=resource_id)
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
        """Whether any of these ids is a permit application this user may see."""
        return cls._visible_permits(user, list(resource_ids)).exists()
