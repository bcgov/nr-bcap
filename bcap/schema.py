"""Custom drf-spectacular AutoSchema subclasses for bcap views."""

import logging

from drf_spectacular.extensions import OpenApiSerializerFieldExtension
from drf_spectacular.openapi import AutoSchema
from rest_framework import serializers

from arches.app.models.models import Node

from arches_querysets.rest_framework.field_mixins import NodeValueMixin
from arches_querysets.rest_framework.serializers import (
    ResourceAliasedDataSerializer,
    TileAliasedDataSerializer,
)

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


def _name_schema():
    # Resource name: an I18n_String serialized to its localized value.
    return {"type": "string", "readOnly": True, "nullable": True}


def _descriptors_schema():
    # Computed display strings keyed by language code (en typed).
    return {
        "type": "object",
        "readOnly": True,
        "nullable": True,
        "properties": {
            "en": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "map_popup": {"type": "string"},
                },
            }
        },
    }


def _provisional_edits_schema():
    # Tile.apply_provisional_edit writes {user_id: provisionaledit}; null once
    # the edit is authoritative.
    return {
        "type": "object",
        "nullable": True,
        "additionalProperties": {
            "type": "object",
            "properties": {
                "value": {"type": "object", "additionalProperties": True},
                "status": {"type": "string"},
                "action": {"type": "string"},
                "reviewer": {"type": "integer", "nullable": True},
                "timestamp": {"type": "string", "nullable": True},
                "reviewtimestamp": {"type": "string", "nullable": True},
            },
        },
    }


# property name -> schema builder for arches base-serializer fields the
# node-value extension never sees (resource name/descriptors, tile
# provisionaledits). Only untyped occurrences are replaced.
_BASE_SERIALIZER_FIELD_SCHEMAS = {
    "name": _name_schema,
    "descriptors": _descriptors_schema,
    "provisionaledits": _provisional_edits_schema,
}


def _is_untyped(schema):
    # The bare {readOnly?, nullable?} drf-spectacular emits for an unannotated
    # field: no type, ref, composition, or nested shape. A node aliased "name"
    # is an allOf/$ref/array and so is left untouched.
    return isinstance(schema, dict) and not (
        schema.keys() & {"type", "$ref", "allOf", "oneOf", "anyOf", "properties"}
    )


def type_base_serializer_fields(result, generator, request, public):
    """Hook: type the arches base-serializer fields the node-value extension can't
    reach (resource name/descriptors, tile provisionaledits), which otherwise stay
    opaque blobs. Only untyped occurrences are replaced."""
    for schema in result.get("components", {}).get("schemas", {}).values():
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            continue
        for field, build in _BASE_SERIALIZER_FIELD_SCHEMAS.items():
            if field in properties and _is_untyped(properties[field]):
                properties[field] = build()
    return result


class AliasedNodeDataSerializer(serializers.Serializer):
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
# Datatypes whose node_value is an array; a required one means >= 1 item.
_ARRAY_NODE_DATATYPES = frozenset(
    {"concept-list", "reference", "resource-instance-list", "file-list"}
)


def _string_node_value(max_length):
    # Localized string: the i18n object the API emits, keyed by language code.
    # A widget maxLength binds to the (en) value, the only typed language.
    value = {"type": "string", "nullable": True}
    if max_length is not None:
        value["maxLength"] = max_length
    return {
        "type": "object",
        "nullable": True,
        "properties": {
            "en": {
                "type": "object",
                "properties": {
                    "value": value,
                    "direction": {"type": "string", "enum": ["ltr", "rtl"]},
                },
            }
        },
    }


def _scalar_string_node_value(max_length):
    # Non-i18n string (also borden numbers); honors a maxLength widget limit.
    schema = {"type": "string", "nullable": True}
    if max_length is not None:
        schema["maxLength"] = max_length
    return schema


def _concept_list_node_value(max_length):
    schema = {
        "type": "array",
        "nullable": True,
        "items": {"type": "string", "format": "uuid"},
    }
    if max_length is not None:
        schema["maxItems"] = max_length
    return schema


def _concept_node_value(max_length):
    return {"type": "string", "format": "uuid", "nullable": True}


def _reference_node_value(max_length):
    label = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "value": {"type": "string"},
            "language_id": {"type": "string"},
            "list_item_id": {"type": "string", "format": "uuid"},
            "valuetype_id": {"type": "string"},
        },
    }
    return {
        "type": "array",
        "nullable": True,
        "items": {
            "type": "object",
            "properties": {
                "uri": {"type": "string"},
                "list_id": {"type": "string", "format": "uuid"},
                "labels": {"type": "array", "items": label},
            },
        },
    }


def _resource_reference():
    return {
        "type": "object",
        "properties": {
            "resourceId": {"type": "string", "format": "uuid"},
            "ontologyProperty": {"type": "string", "nullable": True},
            "resourceXresourceId": {"type": "string", "nullable": True},
            "inverseOntologyProperty": {"type": "string", "nullable": True},
        },
    }


def _resource_instance_node_value(max_length):
    return {**_resource_reference(), "nullable": True}


def _resource_instance_list_node_value(max_length):
    return {"type": "array", "nullable": True, "items": _resource_reference()}


def _file_list_node_value(max_length):
    return {
        "type": "array",
        "nullable": True,
        "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "size": {"type": "number"},
                "type": {"type": "string"},
                "url": {"type": "string", "nullable": True},
                "file": {
                    "type": "object",
                    "properties": {"objectURL": {"type": "string", "nullable": True}},
                },
                "node_id": {"type": "string", "format": "uuid"},
            },
        },
    }


def _url_node_value(max_length):
    return {
        "type": "object",
        "nullable": True,
        "properties": {
            "url": {"type": "string"},
            "url_label": {"type": "string", "nullable": True},
        },
    }


def _geojson_node_value(max_length):
    return {
        "type": "object",
        "nullable": True,
        "properties": {
            "type": {"type": "string"},
            "features": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "type": {"type": "string"},
                        "geometry": {"type": "object", "additionalProperties": True},
                        "properties": {
                            "type": "object",
                            "additionalProperties": True,
                            "nullable": True,
                        },
                    },
                },
            },
        },
    }


# datatype -> node_value shape builder(max_length). Shapes mirror the arches API
# payload; string-family and concept-list honor a widget maxLength, the rest
# ignore it. Datatypes absent here (boolean/date/number) derive node_value from
# the field's base type.
_NODE_VALUE_BUILDERS = {
    "string": _string_node_value,
    "non-localized-string": _scalar_string_node_value,
    "borden-number-datatype": _scalar_string_node_value,
    "concept": _concept_node_value,
    "concept-list": _concept_list_node_value,
    "reference": _reference_node_value,
    "resource-instance": _resource_instance_node_value,
    "resource-instance-list": _resource_instance_list_node_value,
    "file-list": _file_list_node_value,
    "url": _url_node_value,
    "geojson-feature-collection": _geojson_node_value,
}


def _parse_number(raw):
    """Widget min/max come as strings ('' when unset); int when whole, else float."""
    if raw in (None, ""):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return int(value) if value.is_integer() else value


def _number_token(value):
    # Component names allow [A-Za-z0-9._-]; keep the suffix simple and dot-free.
    return str(value).replace("-", "neg").replace(".", "_")


class AliasedNodeDataExtension(OpenApiSerializerFieldExtension):
    """Type the {node_value, display_value, details} envelope per Arches datatype.

    node_value follows the per-datatype shape builders for modeled datatypes and
    the field's base type otherwise; details is typed only for the families that
    emit structured details. get_name() gives each datatype (and each distinct
    maxLength) its own component."""

    target_class = NodeValueMixin
    match_subclasses = True

    def _datatype(self):
        # Arches stamps the datatype onto the field's style.
        return (getattr(self.target, "style", None) or {}).get("datatype")

    def _widget_config(self):
        # The cardxnodexwidget config arches_querysets stamps on, as a plain dict.
        config = (getattr(self.target, "style", None) or {}).get("widget_config")
        if hasattr(config, "serialize"):
            config = config.serialize()
        return config if isinstance(config, dict) else {}

    def _max_length(self):
        # Editors set maxLength on string/concept-list widgets; null when unset.
        raw = self._widget_config().get("maxLength")
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    def _number_bounds(self):
        # Number widgets carry min/max value limits (strings; '' when unset).
        if self._datatype() != "number":
            return None, None
        config = self._widget_config()
        return _parse_number(config.get("min")), _parse_number(config.get("max"))

    def _required(self):
        # arches_querysets sets field.required from Node.isrequired.
        return bool(getattr(self.target, "required", False))

    def _requires_min_items(self):
        return self._datatype() in _ARRAY_NODE_DATATYPES and self._required()

    def _constraint_suffix(self):
        # Differently constrained nodes can't share a datatype's component;
        # encode the limits so equal limits still dedupe to one component.
        parts = []
        max_length = self._max_length()
        if max_length is not None:
            parts.append(f"Max{max_length}")
        minimum, maximum = self._number_bounds()
        if minimum is not None:
            parts.append(f"Min{_number_token(minimum)}")
        if maximum is not None:
            parts.append(f"Max{_number_token(maximum)}")
        if self._requires_min_items():
            parts.append("Required")
        return "".join(parts)

    def get_name(self):
        datatype = self._datatype()
        if not datatype:
            base = "AliasedNodeData"
        else:
            pascal = "".join(p.title() for p in datatype.replace("-", "_").split("_"))
            base = f"{pascal}AliasedNodeData"
        return base + self._constraint_suffix()

    def map_serializer_field(self, auto_schema, direction):
        datatype = self._datatype()
        return {
            "type": "object",
            "properties": {
                "node_value": self._node_value_schema(datatype, auto_schema, direction),
                "display_value": {"type": "string", "readOnly": True},
                "details": self._details_schema(datatype, auto_schema, direction),
            },
            "required": ["node_value"],
        }

    def _node_value_schema(self, datatype, auto_schema, direction):
        """node_value per datatype: a structured shape (mirroring the API payload)
        for modeled datatypes, else the field's base type (boolean/date/number).
        bypass_extensions stops this extension from recursing on the fallback."""
        builder = _NODE_VALUE_BUILDERS.get(datatype)
        if builder is not None:
            schema = builder(self._max_length())
        else:
            schema = auto_schema._map_serializer_field(
                self.target, direction, bypass_extensions=True
            )
            # Number widgets bound the value; map to minimum/maximum.
            minimum, maximum = self._number_bounds()
            if minimum is not None:
                schema["minimum"] = minimum
            if maximum is not None:
                schema["maximum"] = maximum
        if self._requires_min_items():
            schema["minItems"] = 1
        return schema

    def _details_schema(self, datatype, auto_schema, direction):
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
    """Key each aliased_data component name off its graph (and nodegroup, for
    tiles) so drf-spectacular doesn't collapse every graph's aliased_data into
    one shared component."""

    def get_serializer_name(self, serializer, direction):
        # Resource-level aliased_data: the generated serializer class is named
        # the same ("ResourceAliasedData") for every graph, so without this the
        # first graph processed wins and all resources share its fields.
        if isinstance(serializer, ResourceAliasedDataSerializer):
            if serializer.graph_slug:
                kind = (
                    "resource_top_nodegroups_aliased_data"
                    if serializer.Meta.exclude_children
                    else "resource_aliased_data"
                )
                return f"{serializer.graph_slug}_{kind}".title()
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
