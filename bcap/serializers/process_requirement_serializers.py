"""Request serializers for the process-requirement routes. Each wraps a
dataclass, so drf-spectacular documents the body, the frontend's generated types
follow, and the views read validated fields as attributes rather than strings."""

from dataclasses import dataclass, field
from uuid import UUID

from rest_framework import serializers

from rest_framework_dataclasses.serializers import DataclassSerializer


@dataclass
class ReorderRequirements:
    order: list[UUID]


@dataclass
class RequirementStatus:
    satisfied: bool


@dataclass
class RequirementAssignee:
    contributor_id: UUID | None


@dataclass
class ModuleCompletion:
    completed: bool


@dataclass
class AddRequirement:
    name: str = ""


@dataclass
class ChecklistStep:
    name: str
    description: str
    # Omitted for a step the user just added; the backend creates its tile.
    tileid: UUID | None = None


@dataclass
class ChecklistPatch:
    name: str
    steps: list[ChecklistStep]


class ReorderRequirementsSerializer(DataclassSerializer):
    """The reorder PATCH body: the module's requirement resource ids in the new
    order."""

    class Meta:
        dataclass = ReorderRequirements


class RequirementStatusSerializer(DataclassSerializer):
    """The status PATCH body: whether the requirement is satisfied."""

    class Meta:
        dataclass = RequirementStatus


class RequirementAssigneeSerializer(DataclassSerializer):
    """The assignee PATCH body: the Contributor to assign, or null to clear."""

    contributor_id = serializers.UUIDField(allow_null=True)

    class Meta:
        dataclass = RequirementAssignee


class ModuleCompletionSerializer(DataclassSerializer):
    """The module completion PATCH body: whether the module is completed."""

    class Meta:
        dataclass = ModuleCompletion


class AddRequirementSerializer(DataclassSerializer):
    """The add-requirement POST body: an optional name for the blank
    requirement, defaulted server-side when absent."""

    name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        dataclass = AddRequirement


class ChecklistStepSerializer(DataclassSerializer):
    name = serializers.CharField(allow_blank=True)
    description = serializers.CharField(allow_blank=True)

    class Meta:
        dataclass = ChecklistStep


class ChecklistPatchSerializer(DataclassSerializer):
    """The checklist PATCH body: a requirement's name and its full ordered step
    list."""

    name = serializers.CharField(allow_blank=True)
    steps = ChecklistStepSerializer(many=True)

    class Meta:
        dataclass = ChecklistPatch
