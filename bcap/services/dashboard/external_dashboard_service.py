from itertools import chain

from arches_querysets.models import ResourceTileTree

from bcap.util.graph import nodes_for
from bcap.services.bcap_service_request.bcap_service_request_service import (
    BcapServiceRequestService,
)
from bcap.services.dashboard.base_dashboard_service import BaseDashboardService
from bcap.services.message.thread_service import ThreadService
from bcap.services.workflow_draft_service import WorkflowDraftService
from bcap.services.dashboard.dashboard_types import (
    ApplicationCore,
    DashboardFilter,
    ExternalDashboardCard,
    ExternalDashboardPage,
    ExternalDashboardStatus,
    ModuleProgress,
)
from bcap.util.aliases.bcap_service_request import BcapServiceRequestAliases
from bcap.util.aliases.permit_application import PermitApplicationGroupAliases
from bcap.permissions.permit_access import PermitAccess
from bcap.util.aliases.workflow_drafts import WorkflowDraftsAliases
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.dates import to_iso
from bcap.util.user import display_name


class ExternalDashboardService(BaseDashboardService):
    """The applicant-facing dashboard: a user's own BCAP Service Requests, plus
    their drafts. Internal/personal fields are dropped (the creator's name is
    kept). Scoped on created-by (principaluser) for now -- see
    _filter_by_status."""

    SR = BcapServiceRequestAliases

    CARD_NODES = [
        SR.PROJECT_NAME,
        SR.SERVICE_REQUEST_ID,
        SR.SERVICE_REQUEST_TYPE,
        SR.MODULE_ID,
        SR.MODULE_NAME,
        SR.MODULE_ORDER,
        SR.MODULE_COMPLETED_DATE,
        SR.IS_MODULE_COMPLETED,
    ]

    # Service request lifecycle state -> applicant-facing status.
    _STATUS_BY_LIFECYCLE = {
        "Active": "Permit Active",
        "Draft": "Under Review",
    }

    @classmethod
    def base_query(cls, user):
        """The service requests this user filed, card nodes loaded. No staff
        widening: this dashboard answers "my work"."""
        return (
            ResourceTileTree.get_tiles(
                GraphSlugs.BCAP_SERVICE_REQUEST,
                nodes=nodes_for(
                    GraphSlugs.BCAP_SERVICE_REQUEST,
                    cls.CARD_NODES
                    + [
                        cls.SR.APPLICATION_SUBMISSION_DATE,
                        cls.SR.RESPONSIBLE_ORGANIZATION,
                    ],
                ),
                as_representation=True,
            )
            .filter(PermitAccess.own_or_company_service_requests(user))
            .select_related(
                "graph", "principaluser", "resource_instance_lifecycle_state"
            )
            .order_by("pk")  # stable, so LIMIT/OFFSET pages don't overlap
        )

    def get_cards(self, query: DashboardFilter, user) -> ExternalDashboardPage:
        """Cards for the requesting user, one scope per request: drafts, own
        applications, or associated companies'. Status defaults to own
        applications (the serializer supplies FILINGS_CREATED_BY_ME; _filter_by_status
        falls back to the same scope for an unset/unrecognized one)."""
        if query.status in (
            ExternalDashboardStatus.DRAFTS_CREATED_BY_ME,
            ExternalDashboardStatus.DRAFTS_BY_ASSOCIATED_ORGANIZATIONS,
        ):
            count, results = self._draft_cards(user, query)
        else:
            count, results = self._application_cards(query, user)
        return ExternalDashboardPage(
            count=count, page=query.page, limit=query.limit, results=results
        )

    def _application_cards(self, query, user):
        queryset = self._filter_by_status(self.base_query(user), query.status, user)
        count, permits = self._page(queryset, query)
        hca_permits = self._hca_permits(permits)
        unresolved = self._unresolved_counts_by_permit(permits, user.username)
        cards = []
        for permit in permits:
            unresolved_count = unresolved.get(str(permit.pk), 0)
            card = self._application_card(permit, hca_permits, unresolved_count)
            card.module_progress = self._module_progress(permit)
            cards.append(card)
        return count, cards

    def _filter_by_status(self, queryset, status, user):
        """Narrow the base query to the tab asked for."""
        match status:
            case ExternalDashboardStatus.FILINGS_BY_ASSOCIATED_ORGANIZATIONS:
                # Inclusive: the organizations' filings plus the user's own, so
                # the client swaps one list for the other rather than merging.
                return queryset
            case _:
                # Created by me, and anything unrecognized.
                return queryset.filter(principaluser=user)

    def _hca_permits(self, permits):
        """BCAP Service Requests have no HCA permit relationship."""
        return {}

    def _application_core(self, aliased) -> ApplicationCore:
        """The service-request card fields for the external applicant view."""

        def display(alias):
            return self.node_value(aliased, alias).get("display_value", "") or ""

        return ApplicationCore(
            project_name=display(self.SR.PROJECT_NAME),
            application_number=display(self.SR.SERVICE_REQUEST_ID),
            submission_type=display(self.SR.SERVICE_REQUEST_TYPE),
            industrial_sector="",
            priority_level="",
            organization=display(self.SR.RESPONSIBLE_ORGANIZATION),
            related_permit_id=None,
        )

    def _module_progress(self, service_request) -> ModuleProgress:
        """How many modules are complete, and the lowest-ordered outstanding
        one. Traverses service_request_admin instead of application_admin."""
        modules = sorted(
            (
                module.aliased_data
                for admin in self._nested_tiles(
                    service_request.aliased_data.service_request_admin
                )
                for module in self._nested_tiles(admin.aliased_data.process_module)
            ),
            key=lambda data: self._raw_value(data, self.SR.MODULE_ORDER) or 0,
        )
        outstanding = [
            data
            for data in modules
            if not self._raw_value(data, self.SR.IS_MODULE_COMPLETED)
        ]
        return ModuleProgress(
            current_module=(
                self.display_text(self.node_value(outstanding[0], self.SR.MODULE_NAME))
                if outstanding
                else ""
            ),
            completed=len(modules) - len(outstanding),
            total=len(modules),
        )

    def _unresolved_counts_by_permit(
        self, service_requests, username, requirements_by_permit=None
    ):
        """Unresolved thread counts keyed by service request id."""
        contexts = (
            BcapServiceRequestService().submission_context_ids_for_service_requests(
                service_requests, requirements_by_permit
            )
        )
        counts = ThreadService().unresolved_counts_by_context(
            set(chain.from_iterable(contexts.values())), username
        )
        return {
            sr_id: sum(counts.get(cid, 0) for cid in context_ids)
            for sr_id, context_ids in contexts.items()
        }

    def _application_card(self, permit, hca_permits, unresolved_messages=0):
        core = self._application_core(permit.aliased_data)
        return ExternalDashboardCard(
            id=str(permit.pk),
            is_draft=False,
            status=self._status_for(permit),
            created_by_name=display_name(permit.principaluser),
            created_date=to_iso(permit.createdtime),
            submission_date=self._raw_value(
                permit.aliased_data, self.SR.APPLICATION_SUBMISSION_DATE
            )
            or "",
            project_name=core.project_name,
            application_number=core.application_number,
            submission_type=core.submission_type,
            industrial_sector=core.industrial_sector,
            organization=core.organization,
            permit_id=None,
            permit_number="",
            urgency=0,
            priority_level=core.priority_level,
            unresolved_messages=unresolved_messages,
        )

    def _status_for(self, permit):
        lifecycle = permit.resource_instance_lifecycle_state
        # name is an I18n_String (unhashable), so coerce to a plain str before
        # the dict lookup.
        name = str(lifecycle.name) if lifecycle else None
        return self._STATUS_BY_LIFECYCLE.get(name, "")

    def _draft_cards(self, user, query):
        store = WorkflowDraftService()
        own_only = query.status == ExternalDashboardStatus.DRAFTS_CREATED_BY_ME
        count, drafts = self._page(store.base_query(user, own_only=own_only), query)
        unresolved = ThreadService().unresolved_counts_by_context(
            {str(draft.pk) for draft in drafts}, user.username
        )
        parents = self._draft_parents(drafts)
        return count, [
            self._draft_card(
                draft,
                user,
                unresolved.get(str(draft.pk), 0),
                parents.get(WorkflowDraftService.parent_id(draft)),
            )
            for draft in drafts
        ]

    def _draft_parents(self, drafts):
        """Identification of the service requests the drafts were started from,
        keyed by id, so a module draft can name the service request it belongs
        to. A draft's own blob holds nothing about its parent beyond the id."""
        ids = {
            parent
            for draft in drafts
            if (parent := WorkflowDraftService.parent_id(draft))
        }
        if not ids:
            return {}
        service_requests = self._tiles(
            GraphSlugs.BCAP_SERVICE_REQUEST,
            ids,
            [
                self.SR.PROJECT_NAME,
                self.SR.SERVICE_REQUEST_ID,
                self.SR.SERVICE_REQUEST_TYPE,
            ],
        )
        return {
            str(sr.pk): self._application_core(sr.aliased_data)
            for sr in service_requests
        }

    def _draft_card(self, draft, user, unresolved_messages=0, parent=None):
        parent = parent or ApplicationCore()
        ident = self._group_aliased_data(
            {"aliased_data": WorkflowDraftService.blob(draft)},
            PermitApplicationGroupAliases.APPLICATION_IDENTIFICATION,
        )

        def identification(alias, from_parent):
            """The draft's own value, falling back to the permit it hangs off."""
            return self.display_text(ident.get(alias)) or from_parent

        def field(alias):
            return self._raw_value(draft.aliased_data, alias) or ""

        return ExternalDashboardCard(
            id=str(draft.pk),
            is_draft=True,
            graph_slug=field(WorkflowDraftsAliases.GRAPH_SLUG),
            permit_application_id=WorkflowDraftService.parent_id(draft),
            status="Submission Required",
            created_by_name=display_name(draft.principaluser or user),
            created_date=to_iso(draft.createdtime),
            updated_date=field(WorkflowDraftsAliases.UPDATED_DATE),
            project_name=identification(self.PA.PROJECT_NAME, parent.project_name),
            application_number=identification(
                self.PA.APPLICATION_ID, parent.application_number
            ),
            submission_type=identification(self.PA.FILING_TYPE, parent.submission_type),
            organization=parent.organization,
            unresolved_messages=unresolved_messages,
        )
