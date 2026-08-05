"""Company visibility: which organization's members may see a resource."""

from django.db.models import Q, TextField, UUIDField, Value
from django.db.models.fields.json import KeyTextTransform, KeyTransform
from django.db.models.functions import Cast, Coalesce
from django.utils import timezone

from arches.app.models.models import TileModel

from bcap.services.contributor.contributor_service import ContributorService
from bcap.util.aliases.contributor import ContributorAliases
from bcap.util.bcap_aliases import GraphSlugs, RESOURCE_ID
from bcap.util.tiles import resource_instance_value


class OrganizationService(ContributorService):
    """Who may see a resource, by the organization stamped on it.

    Organizations are Contributors too, so this reads the same graph as its
    parent; what it adds is the company-visibility rule. The stamp is recorded
    when a resource is created rather than derived from membership at read time,
    because people change companies: deriving it would carry their old work out
    of the company that paid for it and into the next one.
    """

    def _active_memberships(self):
        """Membership tiles in force today (an unset start/end bound left open),
        each annotated with the org it points at."""
        org_node = self.node_id(
            GraphSlugs.CONTRIBUTOR, ContributorAliases.ASSOCIATED_ORGANIZATION
        )
        start_node = self.node_id(GraphSlugs.CONTRIBUTOR, ContributorAliases.START_DATE)
        end_node = self.node_id(GraphSlugs.CONTRIBUTOR, ContributorAliases.END_DATE)
        membership_ng = self._node_info(
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
                org=Cast(
                    KeyTextTransform(
                        RESOURCE_ID, KeyTransform("0", KeyTransform(org_node, "data"))
                    ),
                    UUIDField(),
                ),
            )
            .filter(_start__lte=today, _end__gte=today)
        )

    def organization_ids(self, username):
        """Ids of the organizations the user belongs to today. The set a
        resource's stamped owning_organization is checked against."""
        my_contributor_id = self.username_contributor_id(username) if username else None
        if not my_contributor_id:
            return set()
        orgs = self._active_memberships().filter(resourceinstance_id=my_contributor_id)
        return {str(org) for org in orgs.values_list("org", flat=True) if org}

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
        """Rows this user may reach: their own, plus their companies'. Unstamped
        rows stay with their creator, so nothing is orphaned by an absent stamp."""
        return Q(principaluser=user) | self.stamped_for(user, alias)

    def stamped_for(self, user, alias):
        """Rows filed under an organization the user is in today, whoever created
        them. Matches nothing when they belong to none -- unlike visible_to, this
        answers "my company's work", not "what I am allowed to see"."""
        scope = Q(pk__in=[])
        for org in self.organization_ids(user.username):
            scope |= Q(**{f"{alias}__contains": resource_instance_value(org)})
        return scope
