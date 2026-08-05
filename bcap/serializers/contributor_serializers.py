"""Shared Contributor response shapes. Thin serializers so drf-spectacular
documents them and the frontend's generated types follow."""

from rest_framework_dataclasses.serializers import DataclassSerializer

from bcap.services.contributor_service import ContributorSummary


class ContributorSummarySerializer(DataclassSerializer):
    """The contributor pick-list option shape, derived from the dataclass."""

    class Meta:
        dataclass = ContributorSummary
