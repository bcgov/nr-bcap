"""bcap delta on top of the arches_zod_validation OpenAPI schema.

Only the date-node override is bcap's own; everything else is re-exported from
arches_zod_validation. Arches date nodes serialize node_value as a bare date
(YYYY-MM-DD) but the field maps to date-time, so we inject a builder that types
it as a date-or-datetime union. Importing this module (the API view mixin does,
via the documented urlconf) installs the override before schema generation reads
the builder table.
"""

from arches_zod_validation import schema as _upstream
from arches_zod_validation.schema import (
    ArchesTileAutoSchema,
    AliasedNodeDataExtension,
    AliasedNodeDataSerializer,
    sort_generated_schema_properties,
    type_base_serializer_fields,
    _sort_properties_in_place,
)

__all__ = [
    "ArchesTileAutoSchema",
    "AliasedNodeDataExtension",
    "AliasedNodeDataSerializer",
    "sort_generated_schema_properties",
    "type_base_serializer_fields",
    "_sort_properties_in_place",
]


def _date_node_value(max_length):
    # Accept a bare date or a full datetime; anyOf becomes a zod union.
    return {
        "nullable": True,
        "anyOf": [
            {"type": "string", "format": "date"},
            {"type": "string", "format": "date-time"},
        ],
    }


# Upstream's datatype -> node_value builder table has no date case, so a date
# node falls through to the base date-time mapping. Inject ours (mutating the
# shared table the active field extension reads) so it emits the union instead.
_upstream._NODE_VALUE_BUILDERS["date"] = _date_node_value
