import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DashboardQuery:
    filter_by: str | None = None
    status: str | None = None
    limit: int = 50
    page: int = 1
    order_by: str | None = None


class DashboardService:
    def get_cards(self, query: DashboardQuery):
        return []
