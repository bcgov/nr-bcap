# Note: We are using snake_case to be consistent with other arches returns.
from rest_framework.serializers import (
    Serializer,
    CharField,
    ChoiceField,
    SerializerMethodField,
    ValidationError,
)
from rest_framework_dataclasses.serializers import DataclassSerializer

from bcap.services.dashboard.dashboard_service import DashboardService
from bcap.services.dashboard.dashboard_types import (
    DashboardPage,
    DashboardFilter,
)


class UserProfileResponseSerializer(Serializer):
    username = CharField()
    first_name = CharField(allow_blank=True)
    last_name = CharField(allow_blank=True)
    groups = SerializerMethodField()

    def get_groups(self, user) -> list[str]:
        return [group.name for group in user.groups.all()]


class DashboardFilterSerializer(DataclassSerializer):
    """The dashboard's query string parameters: an optional contributor filter
    and the paging controls (which page, and how many cards per page)."""

    # Declared so OpenAPI spec advertises the allowed status values as an enum.
    status = ChoiceField(
        choices=[(DashboardService.STATUS_UNASSIGNED, "Unassigned")],
        required=False,
        allow_null=True,
    )

    class Meta:
        dataclass = DashboardFilter

    def validate(self, attrs):
        if attrs.status == DashboardService.STATUS_UNASSIGNED and attrs.contributor_id:
            raise ValidationError(
                "status=UNASSIGNED cannot be combined with contributor_id."
            )
        return attrs


class DashboardPageResponseSerializer(DataclassSerializer):
    """One page of dashboard cards for the current user.

    `count` is the total number of cards matching the query across all pages;
    `page` and `limit` echo the requested page number and page size; `results`
    holds the cards for this page (at most `limit` of them). Each card's fields
    are documented on the DashboardCard dataclass (as field help_text), so the
    per-field descriptions surface in the generated OpenAPI spec.
    """

    class Meta:
        dataclass = DashboardPage
