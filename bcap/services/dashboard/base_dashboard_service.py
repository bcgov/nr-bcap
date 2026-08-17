from itertools import chain

from bcap.services.dashboard.base_graph_service import BaseGraphService
from bcap.services.contributor.contributor_service import ContributorService
from bcap.services.dashboard.dashboard_types import (
    ApplicationCore,
    HcaPermit,
    ModuleProgress,
)
from bcap.services.message.bcap_message_service import BcapMessageService
from bcap.services.permit_application.permit_application_service import (
    PermitApplicationService,
)
from bcap.util.aliases.hca_permit import HCAPermitAliases
from bcap.util.aliases.permit_application import PermitApplicationAliases
from bcap.util.bcap_aliases import GraphSlugs


class BaseDashboardService(BaseGraphService):
    """Shared plumbing for the internal and external dashboards: the contributor
    service, paging, and the related-HCA-permit lookup."""

    PA = PermitApplicationAliases

    CARD_NODES = [
        PA.PROJECT_NAME,
        PA.APPLICATION_ID,
        PA.FILING_TYPE,
        PA.INDUSTRIAL_SECTOR,
        PA.APPLICATION_PRIORITY_LEVEL,
        PA.RELATED_PERMIT,
        PA.MODULE_ID,
        PA.MODULE_NAME,
        PA.MODULE_ORDER,
        PA.MODULE_COMPLETED_DATE,
        PA.IS_MODULE_COMPLETED,
    ]

    def __init__(self):
        self.contributors = ContributorService()

    @staticmethod
    def _page(queryset, query):
        """The query's page of rows and the total count."""
        start = (query.page - 1) * query.limit
        return queryset.count(), list(queryset[start : start + query.limit])

    def _hca_permits(self, permits):
        """Map id -> HcaPermit for the permits' related_permit links."""
        ids = self._referenced_ids(permits, self.PA.RELATED_PERMIT)
        if not ids:
            return {}

        tiles = self._tiles(
            GraphSlugs.HCA_PERMIT,
            ids,
            [HCAPermitAliases.PERMIT_NUMBER, HCAPermitAliases.PERMIT_HOLDER],
        )

        hca_permits = {}
        for permit in tiles:
            data = permit.aliased_data
            hca_permits[str(permit.pk)] = HcaPermit(
                number=self._display_text(
                    self._node_value(data, HCAPermitAliases.PERMIT_NUMBER)
                ),
                holder_ids=self._resource_ids(
                    self._node_value(data, HCAPermitAliases.PERMIT_HOLDER)
                ),
            )
        return hca_permits

    def _application_core(self, aliased):
        """The permit-application card fields common to both dashboards, read off
        the loaded resource tree."""

        def display(alias):
            return self._node_value(aliased, alias).get("display_value", "") or ""

        return ApplicationCore(
            project_name=display(self.PA.PROJECT_NAME),
            application_number=display(self.PA.APPLICATION_ID),
            submission_type=display(self.PA.FILING_TYPE),
            industrial_sector=display(self.PA.INDUSTRIAL_SECTOR),
            priority_level=display(self.PA.APPLICATION_PRIORITY_LEVEL),
            related_permit_id=self._resource_id(
                self._node_value(aliased, self.PA.RELATED_PERMIT)
            ),
        )

    @staticmethod
    def _related_hca(related_permit_id, hca_permits):
        """The HcaPermit a permit application relates to, or an empty one."""
        return hca_permits.get(related_permit_id) or HcaPermit()

    def _unread_counts_by_permit(self, permits, username, requirements_by_permit=None):
        """Unread message counts keyed by permit id, each rolled up across the
        permit's submission contexts (itself plus its requirements' hosts) in a
        single grouped query. When the caller already knows each permit's
        requirement ids, passing them skips re-reading them from the DB."""
        contexts = PermitApplicationService().submission_context_ids_for_permits(
            permits, requirements_by_permit
        )
        counts = BcapMessageService().unread_counts_by_context(
            set(chain.from_iterable(contexts.values())), username
        )
        return {
            permit_id: sum(counts.get(cid, 0) for cid in context_ids)
            for permit_id, context_ids in contexts.items()
        }

    def _module_progress(self, permit) -> ModuleProgress:
        """How many modules are complete, and the lowest-ordered one still
        outstanding. Read off the loaded tree, so no query."""
        modules = sorted(
            (
                module.aliased_data
                for admin in self._nested_tiles(permit.aliased_data.application_admin)
                for module in self._nested_tiles(admin.aliased_data.process_module)
            ),
            key=lambda data: self._raw_value(data, self.PA.MODULE_ORDER) or 0,
        )
        outstanding = [
            data
            for data in modules
            if not self._raw_value(data, self.PA.IS_MODULE_COMPLETED)
        ]
        return ModuleProgress(
            current_module=(
                self._display_text(
                    self._node_value(outstanding[0], self.PA.MODULE_NAME)
                )
                if outstanding
                else ""
            ),
            completed=len(modules) - len(outstanding),
            total=len(modules),
        )
