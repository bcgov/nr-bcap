from bcap.services.dashboard.base_graph_service import BaseGraphService
from bcap.services.dashboard.contributor_service import ContributorService
from bcap.services.dashboard.dashboard_types import ApplicationCore, HcaPermit
from bcap.util.aliases.hca_permit import HCAPermitAliases
from bcap.util.aliases.permit_application import PermitApplicationAliases
from bcap.util.bcap_aliases import GraphSlugs


class BaseDashboardService(BaseGraphService):
    """Shared plumbing for the internal and external dashboards: the contributor
    service, paging, and the related-HCA-permit lookup."""

    PA = PermitApplicationAliases

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

        resources = self._resources(
            GraphSlugs.HCA_PERMIT,
            ids,
            [HCAPermitAliases.PERMIT_NUMBER, HCAPermitAliases.PERMIT_HOLDER],
        )

        hca_permits = {}
        for permit in resources:
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
