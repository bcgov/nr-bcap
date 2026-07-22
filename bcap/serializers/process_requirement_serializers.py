"""Request and host serializers for the process-requirement routes. Thin
serializers so drf-spectacular documents the bodies and the frontend's generated
types follow."""

from drf_spectacular.utils import PolymorphicProxySerializer
from rest_framework import serializers

from arches_zod_validation.views.mixins import BCAPResourceSerializer

from bcap.views.generated.document_submission import DocumentSubmissionSerializer
from bcap.views.generated.information_request import InformationRequestSerializer
from bcap.views.generated.notice_of_project_intent import (
    NoticeOfProjectIntentSerializer,
)
from bcap.views.generated.site_visit import SiteVisitSerializer


# Module host serializers for the graphs with no generated routes of their own
# (their verbs are [] in generate.json); a host is only ever created through the
# module host POST, so these live here. The rest reuse the generated serializer:
# two serializers over one graph would collide as duplicate schema components.
class InvestigationSerializer(BCAPResourceSerializer):
    class Meta(BCAPResourceSerializer.Meta):
        graph_slug = "investigation"


class AlterationSerializer(BCAPResourceSerializer):
    class Meta(BCAPResourceSerializer.Meta):
        graph_slug = "alteration"


class InspectionSerializer(BCAPResourceSerializer):
    class Meta(BCAPResourceSerializer.Meta):
        graph_slug = "inspection"


# The serializer that validates and creates a module's host resource, by host
# graph slug. A module names its host via the child whose resource matches the
# module slug (see template_specs.host_graph); a slug with no group file or no
# host child is rejected before the serializer is reached.
HOST_SERIALIZERS = {
    "investigation": InvestigationSerializer,
    "alteration": AlterationSerializer,
    "inspection": InspectionSerializer,
    "site_visit": SiteVisitSerializer,
    "document_submission": DocumentSubmissionSerializer,
    "information_request": InformationRequestSerializer,
    "notice_of_project_intent": NoticeOfProjectIntentSerializer,
}


def module_host_schema(many):
    """OpenAPI schema for a module host: any one of the registered host types
    (the concrete type depends on the permit_type path segment)."""
    return PolymorphicProxySerializer(
        component_name="ModuleHost",
        serializers=list(HOST_SERIALIZERS.values()),
        resource_type_field_name=None,
        many=many,
    )


class ReorderRequirementsSerializer(serializers.Serializer):
    """The reorder PATCH body: the module's requirement resource ids in the new
    order."""

    order = serializers.ListField(child=serializers.UUIDField())


class RequirementStatusSerializer(serializers.Serializer):
    """The status PATCH body: whether the requirement is satisfied."""

    satisfied = serializers.BooleanField()


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
