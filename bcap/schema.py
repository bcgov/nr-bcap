"""Custom drf-spectacular AutoSchema subclasses for bcap views."""

import logging

from drf_spectacular.extensions import OpenApiSerializerFieldExtension
from drf_spectacular.openapi import AutoSchema
from rest_framework import serializers

from arches.app.models.models import Node

from arches_querysets.rest_framework.field_mixins import NodeValueMixin
from arches_querysets.rest_framework.serializers import TileAliasedDataSerializer

logger = logging.getLogger(__name__)


def _sort_properties_in_place(node, sortorder):
    """Reorder Arches tile-bag properties (all keys node aliases) by node
    sortorder, then alias; leave other maps in declared order."""

    def node_order(alias):
        # Nodes with no sortorder sort last; alias breaks ties.
        sort = sortorder[alias]
        return (sort is None, sort, alias)

    if isinstance(node, list):
        for item in node:
            _sort_properties_in_place(item, sortorder)
    elif isinstance(node, dict):
        props = node.get("properties")
        all_keys_are_nodes = (
            isinstance(props, dict) and props and all(k in sortorder for k in props)
        )
        if all_keys_are_nodes:
            node["properties"] = {k: props[k] for k in sorted(props, key=node_order)}
        for child in node.values():
            _sort_properties_in_place(child, sortorder)


def sort_generated_schema_properties(result, generator, request, public):
    """Hook: order tile-schema properties by node sortorder for stable diffs."""
    # alias -> Node.sortorder, for every node in every graph.
    sortorder = dict(
        Node.objects.exclude(alias=None)
        .order_by("alias", "sortorder")
        .values_list("alias", "sortorder")
    )
    for schema in result.get("components", {}).get("schemas", {}).values():
        _sort_properties_in_place(schema, sortorder)
    return result


class NodeValueEnvelopeSerializer(serializers.Serializer):
    """The {node_value, display_value, details} object node value fields emit when as_representation is True.

    Mirrors the dict built in arches_querysets TileTree.get_value_with_context;
    keep in sync if that shape changes upstream (unit test covers this).
    """

    node_value = serializers.JSONField()
    display_value = serializers.CharField()
    details = serializers.ListField(child=serializers.DictField())


class ConceptValueDetailSerializer(serializers.Serializer):
    """One controlled-list value as serialized into a concept node's `details`
    (arches betterJSONSerializer keys foreign keys by their `_id` attname)."""

    valueid = serializers.UUIDField()
    value = serializers.CharField()
    concept_id = serializers.UUIDField()
    valuetype_id = serializers.CharField()
    language_id = serializers.CharField(allow_null=True)


class ResourceInstanceDetailSerializer(serializers.Serializer):
    """One related resource summarized into a resource-instance node's `details`."""

    resource_id = serializers.UUIDField(allow_null=True)
    display_value = serializers.CharField()


# Datatypes whose get_details() emits a structured list worth typing.
_CONCEPT_DATATYPES = frozenset({"concept", "concept-list"})
_RESOURCE_DATATYPES = frozenset({"resource-instance", "resource-instance-list"})


class NodeValueFieldExtension(OpenApiSerializerFieldExtension):
    """Type the {node_value, display_value, details} envelope per Arches datatype.

    node_value is derived from the field's own underlying type, so new datatypes
    need no changes here; details is typed only for the families that emit
    structured details. get_name() gives each datatype its own component."""

    target_class = NodeValueMixin
    match_subclasses = True

    def _datatype(self):
        # Arches stamps the datatype onto the field's style.
        return (getattr(self.target, "style", None) or {}).get("datatype")

    def get_name(self):
        datatype = self._datatype()
        if not datatype:
            return "NodeValueEnvelope"
        pascal = "".join(p.title() for p in datatype.replace("-", "_").split("_"))
        return f"{pascal}NodeValueEnvelope"

    def map_serializer_field(self, auto_schema, direction):
        # Type node_value from the field's real base (FloatField, DateField, ...);
        # bypass_extensions stops this extension from recursing.
        node_value_schema = auto_schema._map_serializer_field(
            self.target, direction, bypass_extensions=True
        )
        return {
            "type": "object",
            "properties": {
                "node_value": node_value_schema,
                "display_value": {"type": "string", "readOnly": True},
                "details": self._details_schema(auto_schema, direction),
            },
            "required": ["node_value"],
        }

    def _details_schema(self, auto_schema, direction):
        datatype = self._datatype()
        if datatype in _CONCEPT_DATATYPES:
            child = auto_schema.resolve_serializer(
                ConceptValueDetailSerializer, direction
            ).ref
        elif datatype in _RESOURCE_DATATYPES:
            child = auto_schema.resolve_serializer(
                ResourceInstanceDetailSerializer, direction
            ).ref
        else:
            # Scalars emit no structured details; unmodeled datatypes stay generic.
            child = {"type": "object", "additionalProperties": {}}
        return {"type": "array", "items": child, "readOnly": True}


class ArchesTileAutoSchema(AutoSchema):
    """Key each TileAliasedData component name off its nodegroup so drf-spectacular doesn't collapse them all into one."""

    def get_serializer_name(self, serializer, direction):
        if isinstance(serializer, TileAliasedDataSerializer):
            # Resolving .fields runs the DB introspection that pins _root_node
            # to the nodegroup's grouping Node.
            try:
                serializer.fields
            except Exception:
                # Falls through to the default name below; log so a silently
                # un-specialized component name is still traceable.
                logger.debug(
                    "Could not resolve fields for %s; component name not "
                    "specialized by nodegroup.",
                    getattr(serializer, "graph_slug", serializer),
                    exc_info=True,
                )
            root_node = getattr(serializer, "_root_node", None)
            alias = getattr(root_node, "alias", root_node)
            if alias and serializer.graph_slug:
                # Match the "_"-joined Titlecase style of the tile components.
                return f"{serializer.graph_slug}_{alias}_aliased_data".title()
        return super().get_serializer_name(serializer, direction)
