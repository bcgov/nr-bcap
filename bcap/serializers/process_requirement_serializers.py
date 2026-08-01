"""Request serializers for the process-requirement routes. Thin serializers so
drf-spectacular documents the bodies and the frontend's generated types
follow."""

from rest_framework import serializers


class ReorderRequirementsSerializer(serializers.Serializer):
    """The reorder PATCH body: the module's requirement resource ids in the new
    order."""

    order = serializers.ListField(child=serializers.UUIDField())


class RequirementStatusSerializer(serializers.Serializer):
    """The status PATCH body: whether the requirement is satisfied."""

    satisfied = serializers.BooleanField()


class RequirementAssigneeSerializer(serializers.Serializer):
    """The assignee PATCH body: the Contributor to assign, or null to clear."""

    contributor_id = serializers.UUIDField(allow_null=True)


class ModuleCompletionSerializer(serializers.Serializer):
    """The module completion PATCH body: whether the module is completed."""

    completed = serializers.BooleanField()


class AddRequirementSerializer(serializers.Serializer):
    """The add-requirement POST body: an optional name for the blank
    requirement, defaulted server-side when absent."""

    name = serializers.CharField(required=False, allow_blank=True)


class ChecklistStepSerializer(serializers.Serializer):
    # Omit tileid for a step the user just added; the backend creates its tile.
    tileid = serializers.UUIDField(required=False)
    name = serializers.CharField(allow_blank=True)
    description = serializers.CharField(allow_blank=True)


class ChecklistPatchSerializer(serializers.Serializer):
    """The checklist PATCH body: a requirement's name and its full ordered step
    list. Declared as a serializer so the shape reaches the generated client."""

    name = serializers.CharField(allow_blank=True)
    steps = ChecklistStepSerializer(many=True)
