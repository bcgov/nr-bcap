# Note: snake_case to stay consistent with other arches returns.
from rest_framework_dataclasses.serializers import DataclassSerializer

from bcap.services.process_requirement.process_requirement_types import (
    ProcessRequirement,
)


class ProcessRequirementSerializer(DataclassSerializer):
    """A Process Requirement's process dates and its sub-requirements."""

    class Meta:
        dataclass = ProcessRequirement
