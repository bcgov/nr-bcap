"""Company visibility: which organization's members may see a resource."""

from django.db.models import Q, TextField, Value
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Coalesce
from django.utils import timezone

from arches.app.models.models import TileModel

from bcap.util.graph import node_id, node_info
from bcap.services.contributor.contributor_service import ContributorService
from bcap.util.aliases.contributor import ContributorAliases
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.tiles import referenced_resource_ids, resource_instance_value


class OrganizationService(ContributorService):
    """Who may see a resource, by the organization stamped on it.

    Organizations are Contributors too, so this reads the same graph as its
    parent; what it adds is the company-visibility rule. The stamp is recorded
    when a resource is created rather than derived from membership at read time,
    because people change companies: deriving it would carry their old work out
    of the company that paid for it and into the next one.
    """

    def _active_memberships(self):
        """Membership tiles in force today (an unset start/end bound left open)."""
        start_node = node_id(GraphSlugs.CONTRIBUTOR, ContributorAliases.START_DATE)
        end_node = node_id(GraphSlugs.CONTRIBUTOR, ContributorAliases.END_DATE)
        membership_ng = node_info(
            GraphSlugs.CONTRIBUTOR, ContributorAliases.ASSOCIATED_ORGANIZATION
        )[1]
        today = timezone.now().date().isoformat()

        return (
            TileModel.objects.filter(nodegroup_id=membership_ng)
            .annotate(
                _start=Coalesce(
                    KeyTextTransform(start_node, "data"),
                    Value("0000-01-01"),
                    output_field=TextField(),
                ),
                _end=Coalesce(
                    KeyTextTransform(end_node, "data"),
                    Value("9999-12-31"),
                    output_field=TextField(),
                ),
            )
            .filter(_start__lte=today, _end__gte=today)
        )

    def organization_ids(self, username):
        """Ids of the organizations the user belongs to today. The set a
        resource's stamped owning_organization is checked against. A membership
        tile naming several organizations counts for all of them."""
        my_contributor_id = self.username_contributor_id(username) if username else None
        if not my_contributor_id:
            return set()
        tiles = self._active_memberships().filter(resourceinstance_id=my_contributor_id)
        return referenced_resource_ids(
            tiles,
            node_id(GraphSlugs.CONTRIBUTOR, ContributorAliases.ASSOCIATED_ORGANIZATION),
        )

    def resolve_organization(self, user, organization_id=""):
        """The organization id to stamp on something this user is creating.

        A pick is refused unless they belong to it today, so nothing can be filed
        into someone else's company. With no pick: their only organization,
        nothing when they have none, and a refusal when they have several --
        which only they can settle.
        """
        mine = self.organization_ids(user.username)
        if organization_id:
            if str(organization_id) not in mine:
                raise PermissionError("You do not belong to that organization.")
            return str(organization_id)
        if len(mine) > 1:
            raise ValueError("Choose which organization to file this under.")
        return next(iter(mine)) if mine else ""

    def visible_to(self, user, alias):
        """Rows this user may reach: their companies', plus their own when no
        company was named. A stamped row belongs to the organization that paid
        for it, so leaving takes its creator's access with them."""
        return (
            Q(principaluser=user) & self.no_owning_organization(alias)
        ) | self.has_owning_organization_for(user, alias)

    def no_owning_organization(self, alias):
        """Rows naming no organization. Spelled out both ways because a negated
        containment test against a missing value is null, not true."""
        return Q(**{f"{alias}__isnull": True}) | ~Q(**{f"{alias}__contains": [{}]})

    def has_owning_organization_for(self, user, alias):
        """Rows filed under an organization the user is in today, whoever created
        them. Matches nothing when they belong to none -- unlike visible_to, this
        answers "my company's work", not "what I am allowed to see"."""
        scope = Q(pk__in=[])
        for org in self.organization_ids(user.username):
            scope |= Q(**{f"{alias}__contains": resource_instance_value(org)})
        return scope
