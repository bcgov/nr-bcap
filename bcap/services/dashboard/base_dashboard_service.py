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
            # permit_identification is a cardinality-1 top-level group.
            identification = permit.aliased_data.permit_identification.aliased_data
            hca_permits[str(permit.pk)] = HcaPermit(
                number=identification.permit_number["display_value"],
                holder_ids=self._resource_ids(identification.permit_holder),
            )
        return hca_permits

    def _application_core(self, aliased):
        """The permit-application card fields common to both dashboards, read off
        the loaded resource tree."""
        identification = aliased.application_identification.aliased_data
        admin = aliased.application_admin.aliased_data
        return ApplicationCore(
            project_name=identification.project_name["display_value"],
            application_number=identification.application_id["display_value"],
            # industrial_sector is nested two groups deep, so descend with the helper.
            industrial_sector=self._node_value(aliased, self.PA.INDUSTRIAL_SECTOR).get(
                "display_value", ""
            ),
            priority_level=admin.application_priority_level["display_value"],
            # related_permit is cardinality-n; take the first.
            related_permit_id=self._resource_id(
                self._node_value(aliased, self.PA.RELATED_PERMIT)
            ),
        )

    @staticmethod
    def _related_hca(related_permit_id, hca_permits):
        """The HcaPermit a permit application relates to, or an empty one."""
        return hca_permits.get(related_permit_id) or HcaPermit()
