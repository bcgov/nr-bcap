from arches.app.models.models import TileModel

from arches_querysets.models import ResourceTileTree

from bcap.models.resource_draft import ResourceDraft
from bcap.services.dashboard.base_dashboard_service import BaseDashboardService
from bcap.services.dashboard.dashboard_types import (
    DashboardFilter,
    ExternalDashboardCard,
    ExternalDashboardPage,
    ExternalDashboardStatus,
)
from bcap.util.aliases.contributor import ContributorAliases
from bcap.util.aliases.permit_application import PermitApplicationGroupAliases
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.dates import to_iso
from bcap.util.user import display_name


class ExternalDashboardService(BaseDashboardService):
    """The applicant-facing dashboard: a user's own and their associated
    companies' permit applications, plus their drafts. Internal/personal fields
    are dropped (the creator's name is kept). Scoped on created-by
    (principaluser) for now -- see _filter_by_status."""

    # Permit lifecycle state -> applicant-facing status. TODO: confirm the real
    # derivation (no finer workflow signal in the data yet).
    _STATUS_BY_LIFECYCLE = {
        "Active": "Permit Active",
        "Draft": "Under Review",
    }

    def get_cards(self, query: DashboardFilter, user) -> ExternalDashboardPage:
        """Cards for the requesting user, one scope per request: drafts, own
        applications, or associated companies'. Status defaults to own
        applications (the serializer supplies CREATED_BY_ME; _filter_by_status
        falls back to the same scope for an unset/unrecognized one)."""
        if query.status == ExternalDashboardStatus.DRAFTS:
            count, results = self._draft_cards(user, query)
        else:
            count, results = self._application_cards(query, user)
        return ExternalDashboardPage(
            count=count, page=query.page, limit=query.limit, results=results
        )

    def _application_cards(self, query, user):
        queryset = self._filter_by_status(
            self._application_queryset(), query.status, user
        )
        count, permits = self._page(queryset, query)
        hca_permits = self._hca_permits(permits)
        cards = [self._application_card(permit, hca_permits) for permit in permits]
        return count, cards

    def _application_queryset(self):
        return (
            ResourceTileTree.get_tiles(
                GraphSlugs.PERMIT_APPLICATION,
                nodes=self._nodes(
                    GraphSlugs.PERMIT_APPLICATION,
                    [
                        self.PA.PROJECT_NAME,
                        self.PA.APPLICATION_ID,
                        self.PA.APPLICATION_SUBMISSION_DATE,
                        self.PA.INDUSTRIAL_SECTOR,
                        self.PA.APPLICATION_PRIORITY_LEVEL,
                        self.PA.RELATED_PERMIT,
                    ],
                ),
                as_representation=True,
            )
            .select_related(
                "graph", "principaluser", "resource_instance_lifecycle_state"
            )
            .order_by("pk")  # stable, so LIMIT/OFFSET pages don't overlap
        )

    def _filter_by_status(self, queryset, status, user):
        """Created-by scoping. The seam for a future applicant-field match:
        only this method knows how a user/company maps to applications."""
        match status:
            case ExternalDashboardStatus.CREATED_BY_ME:
                return queryset.filter(principaluser=user)
            case ExternalDashboardStatus.CREATED_BY_ASSOCIATED_COMPANIES:
                return queryset.filter(
                    principaluser__username__in=self._company_usernames(user)
                )
            case _:
                # Unrecognized/unset status: scope to own applications.
                return queryset.filter(principaluser=user)

    def _company_usernames(self, user):
        """bcap_usernames of the members of the user's associated companies
        (includes the user). Empty if the user has no linked Contributor."""
        ids = self.contributors.company_contributor_ids(user.username)
        if not ids:
            return set()
        username_node, contributor_ng = self._node_info(
            GraphSlugs.CONTRIBUTOR, ContributorAliases.BCAP_USERNAME
        )
        rows = TileModel.objects.filter(
            nodegroup_id=contributor_ng, resourceinstance_id__in=ids
        ).values_list(f"data__{username_node}", flat=True)
        return {username for username in rows if username}

    def _application_card(self, permit, hca_permits):
        core = self._application_core(permit.aliased_data)
        hca = self._related_hca(core.related_permit_id, hca_permits)
        return ExternalDashboardCard(
            id=str(permit.pk),
            is_draft=False,
            status=self._status_for(permit),
            created_by_name=display_name(permit.principaluser),
            created_date=to_iso(permit.createdtime),
            submission_date=self._raw_value(
                permit.aliased_data, self.PA.APPLICATION_SUBMISSION_DATE
            )
            or "",
            project_name=core.project_name,
            application_number=core.application_number,
            industrial_sector=core.industrial_sector,
            permit_id=core.related_permit_id,
            permit_number=hca.number,
            urgency=0,
            priority_level=core.priority_level,
        )

    def _status_for(self, permit):
        lifecycle = permit.resource_instance_lifecycle_state
        # name is an I18n_String (unhashable), so coerce to a plain str before
        # the dict lookup.
        name = str(lifecycle.name) if lifecycle else None
        return self._STATUS_BY_LIFECYCLE.get(name, "")

    def _draft_queryset(self, user):
        """The user's permit-application drafts, oldest first."""
        return ResourceDraft.objects.filter(
            user=user, graph_slug=GraphSlugs.PERMIT_APPLICATION
        ).order_by("created")

    def _draft_cards(self, user, query):
        count, page = self._page(self._draft_queryset(user), query)
        return count, [self._draft_card(draft, user) for draft in page]

    def _draft_card(self, draft, user):
        ident = self._group_aliased_data(
            draft.data, PermitApplicationGroupAliases.APPLICATION_IDENTIFICATION
        )
        return ExternalDashboardCard(
            id=str(draft.id),
            is_draft=True,
            status="Submission Required",
            created_by_name=display_name(user),
            created_date=to_iso(draft.created),
            project_name=self._display_text(ident.get(self.PA.PROJECT_NAME)),
            application_number=self._display_text(ident.get(self.PA.APPLICATION_ID)),
        )
