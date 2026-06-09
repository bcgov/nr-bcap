from django.db.models import Q, TextField, UUIDField, Value
from django.db.models.fields.json import KeyTextTransform, KeyTransform
from django.db.models.functions import Cast, Coalesce
from django.utils import timezone

from arches.app.models.models import TileModel

from bcap.services.dashboard.base_graph_service import BaseGraphService
from bcap.util.aliases.contributor import ContributorAliases
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.user import full_name


class ContributorService(BaseGraphService):
    """Reads Contributor resources for the dashboard's assignment filters:
    user-to-Contributor, company membership, and display names."""

    A = ContributorAliases

    def username_contributor_id(self, username):
        """Id of the active Contributor with this bcap_username, or None."""
        username_node, contributor_ng = self._node_info(
            GraphSlugs.CONTRIBUTOR, self.A.BCAP_USERNAME
        )
        inactive_node = self._node_id(GraphSlugs.CONTRIBUTOR, self.A.INACTIVE)
        pk = (
            TileModel.objects.filter(
                nodegroup_id=contributor_ng,
                **{f"data__{username_node}": username},
            )
            .exclude(**{f"data__{inactive_node}": True})
            .values_list("resourceinstance_id", flat=True)
            .first()
        )
        return str(pk) if pk else None

    def company_contributor_ids(self, username):
        """The viewer plus the active members of every org the viewer actively
        belongs to today, excluding any flagged inactive."""
        if not username:
            return set()
        my_contributor_id = self.username_contributor_id(username)
        if not my_contributor_id:
            return set()

        org_node = self._node_id(GraphSlugs.CONTRIBUTOR, self.A.ASSOCIATED_ORGANIZATION)
        start_node = self._node_id(GraphSlugs.CONTRIBUTOR, self.A.START_DATE)
        end_node = self._node_id(GraphSlugs.CONTRIBUTOR, self.A.END_DATE)
        inactive_node, contributor_ng = self._node_info(
            GraphSlugs.CONTRIBUTOR, self.A.INACTIVE
        )
        membership_ng = self._node_info(
            GraphSlugs.CONTRIBUTOR, self.A.ASSOCIATED_ORGANIZATION
        )[1]
        today = timezone.now().date().isoformat()

        # Memberships active today (an unset start/end bound left open), each
        # tagged with the org it points at.
        active = (
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
                        "resourceId", KeyTransform("0", KeyTransform(org_node, "data"))
                    ),
                    UUIDField(),
                ),
            )
            .filter(_start__lte=today, _end__gte=today)
        )

        my_orgs = active.filter(resourceinstance_id=my_contributor_id).values("org")
        colleagues = active.filter(org__in=my_orgs).values("resourceinstance_id")

        # The viewer and the active members of those orgs, minus anyone inactive.
        company = (
            TileModel.objects.filter(nodegroup_id=contributor_ng)
            .filter(
                Q(resourceinstance_id=my_contributor_id)
                | Q(resourceinstance_id__in=colleagues)
            )
            .exclude(**{f"data__{inactive_node}": True})
            .values_list("resourceinstance_id", flat=True)
        )
        return {str(pk) for pk in company}

    def names_by_contributor_id(self, ids):
        """Map Contributor id -> "First Last" display name, blank parts skipped."""
        ids = set(ids)
        if not ids:
            return {}
        resources = self._resources(
            GraphSlugs.CONTRIBUTOR,
            ids,
            [self.A.FIRST_NAME, self.A.CONTRIBUTOR_NAME],
        )
        names = {}
        for c in resources:
            data = c.aliased_data.contributor.aliased_data
            first = data.first_name["display_value"]
            last = data.contributor_name["display_value"]
            names[str(c.pk)] = full_name(first, last)
        return names
