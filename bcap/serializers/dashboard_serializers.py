# Note: We are using snake_case to be consistent with other arches returns.
from rest_framework.serializers import (
    Serializer,
    CharField,
    ChoiceField,
    SerializerMethodField,
)
from rest_framework_dataclasses.serializers import DataclassSerializer

from bcap.permissions.groups import is_internal_user
from bcap.services.dashboard.dashboard_types import (
    InternalDashboardPage,
    DashboardFilter,
    ExternalDashboardPage,
    ExternalDashboardStatus,
    InternalDashboardStatus,
)


class UserProfileResponseSerializer(Serializer):
    username = CharField()
    first_name = CharField(allow_blank=True)
    last_name = CharField(allow_blank=True)
    groups = SerializerMethodField()
    is_internal = SerializerMethodField()

    def get_groups(self, user) -> list[str]:
        return [group.name for group in user.groups.all()]

    def get_is_internal(self, user) -> bool:
        """Whether the client should show the Archaeology Branch view. Answered here
        rather than from the group list, so the superuser case and the name of
        the group that marks staff stay in one place."""
        return is_internal_user(user)


class InternalDashboardFilterSerializer(DataclassSerializer):
    """The dashboard's query string parameters: an optional assignment status
    filter and the paging controls (which page, and how many cards per page)."""

    # Declared so OpenAPI spec advertises the allowed status values as an enum.
    status = ChoiceField(choices=InternalDashboardStatus.choices, required=False)

    class Meta:
        dataclass = DashboardFilter


class InternalDashboardPageResponseSerializer(DataclassSerializer):
    """One page of dashboard cards for the current user.

    `count` is the total number of cards matching the query across all pages;
    `page` and `limit` echo the requested page number and page size; `results`
    holds the cards for this page (at most `limit` of them). Each card's fields
    are documented on the InternalDashboardCard dataclass (as field help_text), so the
    per-field descriptions surface in the generated OpenAPI spec.
    """

    class Meta:
        dataclass = InternalDashboardPage


class ExternalDashboardFilterSerializer(DataclassSerializer):
    """Query string parameters for the external dashboard: the scope status
    (drafts / own / associated companies) and the paging controls."""

    status = ChoiceField(
        choices=ExternalDashboardStatus.choices,
        default=ExternalDashboardStatus.FILINGS_CREATED_BY_ME,
    )

    class Meta:
        dataclass = DashboardFilter


class ExternalDashboardPageResponseSerializer(DataclassSerializer):
    """One page of external dashboard cards for the current user.

    `count` is the total number of cards matching the query across all pages;
    `page` and `limit` echo the requested page number and page size; `results`
    holds the cards for this page (at most `limit` of them). Each card's fields
    are documented on the ExternalDashboardCard dataclass (as field help_text),
    so the per-field descriptions surface in the generated OpenAPI spec.
    """

    class Meta:
        dataclass = ExternalDashboardPage
