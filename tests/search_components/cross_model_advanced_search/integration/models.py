from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class NullQualifier(StrEnum):
    HAS_NO_VALUE = "null"
    HAS_ANY_VALUE = "not_null"


class StringQualifier(StrEnum):
    EQUALS = "eq"
    LIKE = "~"
    NOT = "!eq"
    NOT_LIKE = "!~"


class NumberQualifier(StrEnum):
    EQUALS = "eq"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"


class DateQualifier(StrEnum):
    EQUALS = "eq"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"


class BooleanQualifier(StrEnum):
    FALSE = "f"
    TRUE = "t"


class GeometryQualifier(StrEnum):
    LINE_STRING = "LineString"
    POINT = "Point"
    POLYGON = "Polygon"


class Datatype(StrEnum):
    BOOLEAN = "boolean"
    BORDEN_NUMBER = "borden-number-datatype"
    CONCEPT = "concept"
    CONCEPT_LIST = "concept-list"
    DATE = "date"
    DOMAIN_VALUE = "domain-value"
    DOMAIN_VALUE_LIST = "domain-value-list"
    EDTF = "edtf"
    FILE_LIST = "file-list"
    GEOJSON = "geojson-feature-collection"
    NON_LOCALIZED_STRING = "non-localized-string"
    NUMBER = "number"
    REFERENCE = "reference"
    RESOURCE_INSTANCE = "resource-instance"
    RESOURCE_INSTANCE_LIST = "resource-instance-list"
    STRING = "string"
    URL = "url"


VAL_QUALIFIERS = {*BooleanQualifier, *GeometryQualifier}

STRING_DATATYPES = {Datatype.BORDEN_NUMBER, Datatype.NON_LOCALIZED_STRING, Datatype.STRING}
NUMBER_DATATYPES = {Datatype.NUMBER}
DATE_DATATYPES = {Datatype.DATE}
BOOLEAN_DATATYPES = {Datatype.BOOLEAN}
GEO_DATATYPES = {Datatype.GEOJSON}

NO_INPUT_QUALIFIERS = {*NullQualifier, *BooleanQualifier, *GeometryQualifier}


def get_qualifiers_for(datatype: str) -> set[str]:
    base = set(NullQualifier)

    if datatype in STRING_DATATYPES:
        return base | set(StringQualifier)

    if datatype in NUMBER_DATATYPES:
        return base | set(NumberQualifier)

    if datatype in DATE_DATATYPES:
        return base | set(DateQualifier)

    if datatype in BOOLEAN_DATATYPES:
        return base | set(BooleanQualifier)

    if datatype in GEO_DATATYPES:
        return base | set(GeometryQualifier)

    return base


def qualifier_needs_value(qualifier: str, datatype: str) -> bool:
    if qualifier in NO_INPUT_QUALIFIERS:
        return False

    if datatype in STRING_DATATYPES:
        return qualifier in set(StringQualifier)

    if datatype in NUMBER_DATATYPES:
        return qualifier in set(NumberQualifier)

    if datatype in DATE_DATATYPES:
        return qualifier in set(DateQualifier)

    return False


@dataclass
class NodeInfo:
    datatype: str
    label: str
    node_id: str


@dataclass
class CardInfo:
    card_name: str
    graph_id: str
    graph_name: str
    nodegroup_id: str
    nodes: list[NodeInfo]
    slug: str

    @classmethod
    def from_dict(cls, data: dict) -> CardInfo:
        return cls(
            card_name=data["card_name"],
            graph_id=data["graph_id"],
            graph_name=data["graph_name"],
            nodegroup_id=data["nodegroup_id"],
            nodes=[NodeInfo(**n) for n in data["nodes"]],
            slug=data["slug"],
        )

    @property
    def node_lookup(self) -> dict[str, NodeInfo]:
        return {n.label: n for n in self.nodes}

    @property
    def test_id(self) -> str:
        g = self.graph_name.replace(" ", "_")
        c = self.card_name.replace(" ", "_").replace(".", "")
        return f"{g}__{c}"


@dataclass
class FieldInfo:
    index: int
    label: str
    qualifiers: list[str]


@dataclass
class CMFieldInfo:
    label: str
    node_id: str
    qualifiers: list[str]


@dataclass
class QualifierTestItem:
    cache_key: str
    label: str
    node_id: str
    qualifier: str
    text: str = ""

    @property
    def display(self) -> str:
        return f"{self.label} [{self.cache_key}]"

    @classmethod
    def from_cache_key(cls, label: str, node_id: str, cache_key: str) -> QualifierTestItem:
        if ":" in cache_key:
            qualifier, text = cache_key.split(":", 1)
        else:
            qualifier, text = cache_key, ""

        return cls(
            cache_key=cache_key,
            label=label,
            node_id=node_id,
            qualifier=qualifier,
            text=text,
        )


@dataclass
class Mismatch:
    adv_count: int
    cm_count: int
    display: str

    def __str__(self) -> str:
        return f"{self.display}: Advanced={self.adv_count}, CrossModel={self.cm_count}"
