"""One resource serializer per graph, and the helpers that document a route
accepting or returning more than one of them as a union.

Registered here rather than per-route so the routes that span several graphs
(module hosts, workflow drafts) read from one list: two serializers over the
same graph would collide as duplicate schema components.
"""

from drf_spectacular.utils import PolymorphicProxySerializer

from arches_zod_validation.views.mixins import BCAPResourceSerializer

from bcap.schema import resource_aliased_data_component
from bcap.util.bcap_aliases import GraphSlugs
from bcap.views.generated.document_submission import DocumentSubmissionSerializer
from bcap.views.generated.information_request import InformationRequestSerializer
from bcap.views.generated.notice_of_project_intent import (
    NoticeOfProjectIntentSerializer,
)
from bcap.views.generated.permit_application import PermitApplicationSerializer
from bcap.views.generated.site_visit import SiteVisitSerializer


# Graphs whose verbs are [] in generate.json have no generated route, so no
# generated serializer either; declare theirs here. The rest reuse the
# generated one.
class InvestigationSerializer(BCAPResourceSerializer):
    class Meta(BCAPResourceSerializer.Meta):
        graph_slug = GraphSlugs.INVESTIGATION


class AlterationSerializer(BCAPResourceSerializer):
    class Meta(BCAPResourceSerializer.Meta):
        graph_slug = GraphSlugs.ALTERATION


class InspectionSerializer(BCAPResourceSerializer):
    class Meta(BCAPResourceSerializer.Meta):
        graph_slug = GraphSlugs.INSPECTION


GRAPH_SERIALIZERS = {
    GraphSlugs.ALTERATION: AlterationSerializer,
    GraphSlugs.DOCUMENT_SUBMISSION: DocumentSubmissionSerializer,
    GraphSlugs.INFORMATION_REQUEST: InformationRequestSerializer,
    GraphSlugs.INSPECTION: InspectionSerializer,
    GraphSlugs.INVESTIGATION: InvestigationSerializer,
    GraphSlugs.NOTICE_OF_PROJECT_INTENT: NoticeOfProjectIntentSerializer,
    GraphSlugs.PERMIT_APPLICATION: PermitApplicationSerializer,
    GraphSlugs.SITE_VISIT: SiteVisitSerializer,
}


# Host resource serializers, by host graph slug: every graph but
# permit_application, the parent a module hangs off rather than a host.
MODULE_SERIALIZERS = {
    slug: serializer
    for slug, serializer in GRAPH_SERIALIZERS.items()
    if slug != GraphSlugs.PERMIT_APPLICATION
}


def module_host_schema(many):
    """OpenAPI schema for a module host: any one of the registered host types
    (the concrete type depends on the permit_type path segment)."""
    return PolymorphicProxySerializer(
        component_name="ModuleHost",
        serializers=list(MODULE_SERIALIZERS.values()),
        resource_type_field_name=None,
        many=many,
    )


def aliased_data_union_schema():
    """OpenAPI schema for a route carrying a bare aliased_data blob (a workflow
    draft): any one registered graph's aliased_data. Refers to the components
    the resource serializers above already emit rather than introspecting the
    graphs again, which would mint a second set of same-named tile components."""
    return {
        "oneOf": [
            {"$ref": "#/components/schemas/" + resource_aliased_data_component(slug)}
            for slug in GRAPH_SERIALIZERS
        ]
    }
