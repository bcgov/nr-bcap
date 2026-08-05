from arches_querysets.models import ResourceTileTree

from bcap.services.dashboard.base_dashboard_service import BaseDashboardService
from bcap.services.message.bcap_message_service import BcapMessageService
from bcap.services.contributor.organization_service import OrganizationService
from bcap.services.workflow_draft_service import WorkflowDraftService
from bcap.services.dashboard.dashboard_types import (
    ApplicationCore,
    DashboardFilter,
    ExternalDashboardCard,
    ExternalDashboardPage,
    ExternalDashboardStatus,
)
from bcap.util.aliases.permit_application import PermitApplicationGroupAliases
from bcap.util.aliases.workflow_drafts import WorkflowDraftsAliases
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
        unread = self._unread_counts_by_permit(permits, user.username)
        cards = []
        for permit in permits:
            unread_count = unread.get(str(permit.pk), 0)
            card = self._application_card(permit, hca_permits, unread_count)
            card.module_progress = self._module_progress(permit)
            cards.append(card)
        return count, cards

    def _application_queryset(self):
        return (
            ResourceTileTree.get_tiles(
                GraphSlugs.PERMIT_APPLICATION,
                nodes=self.nodes(
                    GraphSlugs.PERMIT_APPLICATION,
                    [
                        self.PA.PROJECT_NAME,
                        self.PA.APPLICATION_ID,
                        self.PA.APPLICATION_SUBMISSION_DATE,
                        self.PA.FILING_TYPE,
                        self.PA.INDUSTRIAL_SECTOR,
                        self.PA.APPLICATION_PRIORITY_LEVEL,
                        self.PA.RELATED_PERMIT,
                        self.PA.MODULE_ID,
                        self.PA.MODULE_NAME,
                        self.PA.MODULE_ORDER,
                        self.PA.MODULE_COMPLETED_DATE,
                        self.PA.IS_MODULE_COMPLETED,
                        self.PA.OWNING_ORGANIZATION,
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
                    OrganizationService().stamped_for(user, self.PA.OWNING_ORGANIZATION)
                )
            case _:
                # Unrecognized/unset status: scope to own applications.
                return queryset.filter(principaluser=user)

    def _application_card(self, permit, hca_permits, unread_messages=0):
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
            submission_type=core.submission_type,
            industrial_sector=core.industrial_sector,
            permit_id=core.related_permit_id,
            permit_number=hca.number,
            urgency=0,
            priority_level=core.priority_level,
            unread_messages=unread_messages,
        )

    def _status_for(self, permit):
        lifecycle = permit.resource_instance_lifecycle_state
        # name is an I18n_String (unhashable), so coerce to a plain str before
        # the dict lookup.
        name = str(lifecycle.name) if lifecycle else None
        return self._STATUS_BY_LIFECYCLE.get(name, "")

    def _draft_cards(self, user, query):
        store = WorkflowDraftService()
        count, drafts = self._page(store.queryset(user), query)
        unread = BcapMessageService().unread_counts_by_context(
            {str(draft.pk) for draft in drafts}, user.username
        )
        parents = self._draft_parents(drafts)
        return count, [
            self._draft_card(
                draft,
                user,
                unread.get(str(draft.pk), 0),
                parents.get(WorkflowDraftService.parent_id(draft)),
            )
            for draft in drafts
        ]

    def _draft_parents(self, drafts):
        """Identification of the permit applications the drafts were started
        from, keyed by id, so a module draft can name the permit it belongs to.
        A draft's own blob holds nothing about its parent beyond the id."""
        ids = {
            parent
            for draft in drafts
            if (parent := WorkflowDraftService.parent_id(draft))
        }
        if not ids:
            return {}
        permits = self._tiles(
            GraphSlugs.PERMIT_APPLICATION,
            ids,
            [self.PA.PROJECT_NAME, self.PA.APPLICATION_ID, self.PA.FILING_TYPE],
        )
        return {
            str(permit.pk): self._application_core(permit.aliased_data)
            for permit in permits
        }

    def _draft_card(self, draft, user, unread_messages=0, parent=None):
        parent = parent or ApplicationCore()
        ident = self._group_aliased_data(
            {"aliased_data": WorkflowDraftService.blob(draft)},
            PermitApplicationGroupAliases.APPLICATION_IDENTIFICATION,
        )

        def identification(alias, from_parent):
            """The draft's own value, falling back to the permit it hangs off."""
            return self._display_text(ident.get(alias)) or from_parent

        def field(alias):
            return self._raw_value(draft.aliased_data, alias) or ""

        return ExternalDashboardCard(
            id=str(draft.pk),
            is_draft=True,
            graph_slug=field(WorkflowDraftsAliases.GRAPH_SLUG),
            permit_application_id=WorkflowDraftService.parent_id(draft),
            status="Submission Required",
            created_by_name=display_name(user),
            created_date=to_iso(draft.createdtime),
            updated_date=field(WorkflowDraftsAliases.UPDATED_DATE),
            project_name=identification(self.PA.PROJECT_NAME, parent.project_name),
            application_number=identification(
                self.PA.APPLICATION_ID, parent.application_number
            ),
            submission_type=identification(self.PA.FILING_TYPE, parent.submission_type),
            unread_messages=unread_messages,
        )
