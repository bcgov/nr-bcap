# Note: We are using snake_case to be consistent with other arches returns.
from rest_framework.serializers import (
    Serializer,
    CharField,
    SerializerMethodField,
)
from rest_framework_dataclasses.serializers import DataclassSerializer

from bcap.services.dashboard.dashboard_types import (
    DashboardPage,
    DashboardFilter,
)


class UserProfileResponseSerializer(Serializer):
    username = CharField()
    first_name = CharField(allow_blank=True)
    last_name = CharField(allow_blank=True)
    groups = SerializerMethodField()
    contributor_id = SerializerMethodField()

    def get_groups(self, user) -> list[str]:
        return [group.name for group in user.groups.all()]

    def get_contributor_id(self, user) -> str | None:
        """TODO fill this in."""
        pass


class DashboardFilterSerializer(DataclassSerializer):
    """The dashboard's query string parameters: an optional contributor filter
    and the paging controls (which page, and how many cards per page)."""

    class Meta:
        dataclass = DashboardFilter


class DashboardPageResponseSerializer(DataclassSerializer):
    """One page of dashboard cards for the current user.

    `count` is the total number of cards matching the query across all pages;
    `page` and `limit` echo the requested page number and page size; `results`
    holds the cards for this page (at most `limit` of them).
    """

    class Meta:
        dataclass = DashboardPage
