from __future__ import annotations

import hashlib
import json
import logging

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from typing_extensions import Any

from django.contrib.auth.models import User
from django.db.models import Q
from django.test import RequestFactory

from arches.app.models.concept import Concept
from arches.app.models.models import CardModel, GraphModel, Node, ResourceInstance
from arches.app.search.elasticsearch_dsl_builder import Bool
from arches.app.search.mappings import RESOURCES_INDEX
from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.utils.betterJSONSerializer import JSONSerializer
from arches_controlled_lists.models import List, ListItemValue

from bcap.search_components.cross_model_advanced_search import CrossModelAdvancedSearch


log = logging.getLogger(__name__)


BASELINE_FILE = Path(__file__).parent / "cross_model_search_baselines.json"
TEST_CASES_FILE = Path(__file__).parent / "test_cases.json"


class DataType(StrEnum):
    BOOLEAN = "boolean"
    CONCEPT = "concept"
    CONCEPT_LIST = "concept-list"
    CONTROLLED_LIST = "controlled-list-datatype"
    DATE = "date"
    EDTF = "edtf"
    NON_LOCALIZED_STRING = "non-localized-string"
    NUMBER = "number"
    REFERENCE = "reference"
    RESOURCE_INSTANCE = "resource-instance"
    RESOURCE_INSTANCE_LIST = "resource-instance-list"
    STRING = "string"


class Language(StrEnum):
    EN = "en"


class LogicalOperator(StrEnum):
    AND = "and"
    OR = "or"


class MatchType(StrEnum):
    ALL = "all"
    ANY = "any"


class Operator(StrEnum):
    CONTAINS = "~"
    EMPTY = ""
    EQ = "eq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    NEQ = "!eq"


class ResultOperation(StrEnum):
    INTERSECT = "intersect"
    UNION = "union"


class TranslateMode(StrEnum):
    NONE = "none"


@dataclass(frozen=True)
class CardFilterData:
    filters: dict[str, FilterValue]
    nodegroup_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "filters": {k: v.to_dict() for k, v in self.filters.items()},
            "nodegroup_id": self.nodegroup_id,
        }


@dataclass(frozen=True)
class FilterDefinition:
    card_name: str
    graph_name: str
    node_name: str
    value: str
    operator: Operator = Operator.EQ

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FilterDefinition:
        return cls(
            card_name=data["card_name"],
            graph_name=data["graph_name"],
            node_name=data["node_name"],
            operator=Operator(data.get("operator", "eq")),
            value=data["value"],
        )


@dataclass(frozen=True)
class FilterValue:
    op: Operator
    val: Any
    lang: Language | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {"op": self.op, "val": self.val}

        if self.lang is not None:
            result["lang"] = self.lang

        return result


@dataclass(frozen=True)
class GroupData:
    cards: list[CardFilterData]
    match: MatchType = MatchType.ALL
    operator_after: LogicalOperator = LogicalOperator.AND

    def to_dict(self) -> dict[str, Any]:
        return {
            "cards": [c.to_dict() for c in self.cards],
            "match": self.match,
            "operator_after": self.operator_after,
        }


@dataclass(frozen=True)
class QueryData:
    result_operation: ResultOperation
    sections: list[SectionData]
    strict_mode: bool
    translate_mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_operation": self.result_operation,
            "sections": [s.to_dict() for s in self.sections],
            "strict_mode": self.strict_mode,
            "translate_mode": self.translate_mode,
        }


@dataclass(frozen=True)
class SectionData:
    graph_id: str
    groups: list[GroupData]

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "groups": [g.to_dict() for g in self.groups],
        }


@dataclass(frozen=True)
class SnapshotCase:
    name: str
    filters: tuple[FilterDefinition, ...] = field(default_factory=tuple)
    intersection_targets: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SnapshotCase:
        return cls(
            filters=tuple(FilterDefinition.from_dict(f) for f in data.get("filters", [])),
            intersection_targets=tuple(data.get("intersection_targets", [])),
            name=data["name"],
        )


@dataclass(frozen=True)
class TestResult:
    baseline_count: int | None
    current_count: int
    intersection_target: str
    passed: bool
    test_name: str


def extract_name(name_field: Any) -> str:
    if name_field is None:
        return ""

    if isinstance(name_field, dict):
        return name_field.get(Language.EN) or next(iter(name_field.values()), "")

    return str(name_field)


def load_test_cases(path: Path = TEST_CASES_FILE) -> list[SnapshotCase]:
    if not path.exists():
        return []

    with open(path, "r") as f:
        raw = json.load(f)

    return [SnapshotCase.from_dict(tc) for tc in raw]


class BaselineManager:
    def __init__(self, baseline_file: Path = BASELINE_FILE) -> None:
        self.baseline_file = baseline_file
        self.baselines = self._load()

    def _load(self) -> dict[str, int]:
        if not self.baseline_file.exists():
            return {}

        with open(self.baseline_file, "r") as f:
            return json.load(f)

    def get(self, key: str) -> int | None:
        return self.baselines.get(key)

    def save(self) -> None:
        with open(self.baseline_file, "w") as f:
            json.dump(self.baselines, f, indent=4, sort_keys=True)

    def update(self, key: str, value: int) -> None:
        self.baselines[key] = value


class FilterValueBuilder:
    BOOLEAN_FALSE_VALUES = frozenset({"0", "f", "false", "n", "no", "off", "permitted"})
    BOOLEAN_TRUE_VALUES = frozenset({"1", "on", "t", "true", "y", "yes"})
    CONCEPT_TYPES = frozenset({DataType.CONCEPT, DataType.CONCEPT_LIST})
    CONTROLLED_LIST_TYPES = frozenset({DataType.CONTROLLED_LIST, DataType.REFERENCE})
    NUMERIC_TYPES = frozenset({DataType.NUMBER, DataType.EDTF})
    RESOURCE_TYPES = frozenset({DataType.RESOURCE_INSTANCE, DataType.RESOURCE_INSTANCE_LIST})
    STRING_TYPES = frozenset({DataType.STRING, DataType.NON_LOCALIZED_STRING})

    def _build_boolean_value(self, value: str, operator: Operator) -> FilterValue:
        value_lower = value.lower().strip()

        if value_lower in self.BOOLEAN_TRUE_VALUES:
            return FilterValue(op=operator, val="t")

        if value_lower in self.BOOLEAN_FALSE_VALUES:
            return FilterValue(op=operator, val="f")

        return FilterValue(op=operator, val="t" if value else "f")

    def _build_concept_value(
        self,
        node: Node,
        value: str,
        operator: Operator,
    ) -> FilterValue | None:
        concept_filter = Q(value__icontains=value)
        nodetype = node.config.get("rdmCollection") if node.config else None

        if nodetype:
            concept_filter &= Q(concept__nodetype_id=nodetype)

        matches = Concept.objects.filter(concept_filter).values_list(
            "concept__legacyoid", flat=True
        )[:1]

        if not matches:
            log.warning(f"No concept match for '{value}' on node {extract_name(node.name)}")
            return None

        return FilterValue(op=operator, val=str(matches[0]))

    def _build_controlled_list_value(
        self,
        node: Node,
        value: str,
        operator: Operator,
    ) -> FilterValue | None:
        config = node.config or {}
        controlled_list_id = config.get("controlledList")

        if not controlled_list_id:
            log.warning(f"Node {extract_name(node.name)} has no controlledList config")
            return None

        controlled_list = List.objects.filter(id=controlled_list_id).first()

        if not controlled_list:
            log.warning(f"Controlled list not found: {controlled_list_id}")
            return None

        list_item_value = ListItemValue.objects.filter(
            Q(value__iexact=value) | Q(value__icontains=value),
            list_item__list_id=controlled_list_id,
        ).select_related("list_item").first()

        if not list_item_value:
            log.warning(
                f"ListItemValue not found for value '{value}' in list '{controlled_list.name}'"
            )
            return None

        list_item = list_item_value.list_item

        if not list_item.uri:
            log.warning(f"ListItem {list_item.id} has no URI")
            return None

        return FilterValue(
            op=operator,
            val=[
                {
                    "labels": [{"list_item_id": str(list_item.id)}],
                    "uri": str(list_item.uri),
                }
            ],
        )

    def _build_date_value(self, value: str, operator: Operator) -> FilterValue:
        if value.startswith(">"):
            return FilterValue(op=Operator.GT, val=value[1:])

        if value.startswith("<"):
            return FilterValue(op=Operator.LT, val=value[1:])

        return FilterValue(op=operator, val=value)

    def _build_resource_instance_value(
        self,
        node: Node,
        value: str,
        operator: Operator,
    ) -> FilterValue | None:
        matches = ResourceInstance.objects.filter(
            name__icontains=value,
        ).values_list("resourceinstanceid", flat=True)[:5]

        if not matches:
            log.warning(f"No resource instance match for '{value}'")
            return None

        return FilterValue(
            op=operator,
            val=[{"resourceId": str(rid)} for rid in matches],
        )

    def build(self, node: Node, value: str, operator: Operator) -> FilterValue | None:
        datatype = node.datatype

        if datatype == DataType.BOOLEAN:
            return self._build_boolean_value(value, operator)

        if datatype in self.CONCEPT_TYPES:
            return self._build_legacy_concept_value(node, value, operator)

        if datatype in self.CONTROLLED_LIST_TYPES:
            return self._build_controlled_list_value(node, value, operator)

        if datatype == DataType.DATE:
            return self._build_date_value(value, operator)

        if datatype in self.NUMERIC_TYPES:
            return FilterValue(op=operator, val=value)

        if datatype in self.RESOURCE_TYPES:
            return self._build_resource_instance_value(node, value, operator)

        if datatype in self.STRING_TYPES:
            return FilterValue(op=Operator.CONTAINS, val=value, lang=Language.EN)

        log.warning(f"Unhandled datatype '{datatype}' for node {extract_name(node.name)}")

        return FilterValue(op=operator, val=value)


class ModelCache:
    def __init__(self) -> None:
        self._cards: dict[tuple[str, str], CardModel] = {}
        self._graphs: dict[str, GraphModel] = {}
        self._nodes: dict[tuple[str, str, str], Node] = {}

    def _find_match(
        self,
        items: list[Any],
        target: str,
        name_extractor: Any,
    ) -> Any | None:
        target_lower = target.lower()
        exact_match = None
        partial_match = None

        for item in items:
            name = name_extractor(item).lower()

            if name == target_lower:
                exact_match = item
                break

            if partial_match is None and target_lower in name:
                partial_match = item

        return exact_match or partial_match

    def get_card(self, graph_name: str, card_name: str) -> CardModel | None:
        cache_key = (graph_name.lower(), card_name.lower())

        if cache_key in self._cards:
            return self._cards[cache_key]

        graph = self.get_graph(graph_name)

        if not graph:
            return None

        cards = list(CardModel.objects.filter(graph=graph).select_related("nodegroup"))
        result = self._find_match(cards, card_name, lambda c: extract_name(c.name))

        if result:
            self._cards[cache_key] = result

        return result

    def get_graph(self, graph_name: str) -> GraphModel | None:
        cache_key = graph_name.lower()

        if cache_key in self._graphs:
            return self._graphs[cache_key]

        graphs = list(GraphModel.objects.filter(is_active=True, isresource=True))
        result = self._find_match(graphs, graph_name, lambda g: extract_name(g.name))

        if result:
            self._graphs[cache_key] = result

        return result

    def get_node(self, graph_name: str, card_name: str, node_name: str) -> Node | None:
        cache_key = (graph_name.lower(), card_name.lower(), node_name.lower())

        if cache_key in self._nodes:
            return self._nodes[cache_key]

        card = self.get_card(graph_name, card_name)

        if not card:
            return None

        nodes = list(Node.objects.filter(nodegroup_id=card.nodegroup_id))
        result = self._find_match(nodes, node_name, lambda n: extract_name(n.name))

        if result:
            self._nodes[cache_key] = result

        return result


class QueryBuilder:
    def __init__(self) -> None:
        self.filter_value_builder = FilterValueBuilder()
        self.model_cache = ModelCache()

    def _build_card_filter(
        self,
        filter_def: FilterDefinition,
    ) -> tuple[str, str, str, FilterValue] | None:
        graph = self.model_cache.get_graph(filter_def.graph_name)

        if not graph:
            log.warning(f"Graph not found: {filter_def.graph_name}")
            return None

        card = self.model_cache.get_card(filter_def.graph_name, filter_def.card_name)

        if not card:
            log.warning(f"Card not found: {filter_def.card_name} in {filter_def.graph_name}")
            return None

        node = self.model_cache.get_node(
            filter_def.graph_name,
            filter_def.card_name,
            filter_def.node_name,
        )

        if not node:
            log.warning(f"Node not found: {filter_def.node_name} in {filter_def.card_name}")
            return None

        filter_value = self.filter_value_builder.build(node, filter_def.value, filter_def.operator)

        if filter_value is None:
            log.warning(
                f"Could not build filter value for: {filter_def.node_name} = {filter_def.value}"
            )
            return None

        return str(graph.graphid), str(card.nodegroup_id), str(node.nodeid), filter_value

    def build(self, test_case: SnapshotCase, intersection_target: str) -> QueryData:
        filters_by_card: dict[tuple[str, str], dict[str, FilterValue]] = {}

        for filter_def in test_case.filters:
            result = self._build_card_filter(filter_def)

            if result is None:
                continue

            graph_id, nodegroup_id, node_id, filter_value = result
            key = (graph_id, nodegroup_id)

            if key not in filters_by_card:
                filters_by_card[key] = {}

            filters_by_card[key][node_id] = filter_value

        sections_by_graph: dict[str, list[CardFilterData]] = {}

        for (graph_id, nodegroup_id), filters in filters_by_card.items():
            if graph_id not in sections_by_graph:
                sections_by_graph[graph_id] = []

            sections_by_graph[graph_id].append(
                CardFilterData(filters=filters, nodegroup_id=nodegroup_id)
            )

        sections = [
            SectionData(
                graph_id=graph_id,
                groups=[GroupData(cards=cards)],
            )
            for graph_id, cards in sections_by_graph.items()
        ]

        translate_mode = TranslateMode.NONE
        strict_mode = False

        if intersection_target and intersection_target != TranslateMode.NONE:
            graph = self.model_cache.get_graph(intersection_target)

            if graph and graph.slug:
                translate_mode = str(graph.slug)
                strict_mode = True

        return QueryData(
            result_operation=ResultOperation.INTERSECT,
            sections=sections,
            strict_mode=strict_mode,
            translate_mode=translate_mode,
        )


class _QueryWrapper:
    def __init__(self) -> None:
        self._bool = Bool()

    def add_query(self, query: Bool) -> None:
        self._bool.must(query)

    @property
    def dsl(self) -> dict[str, Any]:
        return self._bool.dsl


class SearchExecutor:
    def __init__(self, user: Any = None) -> None:
        self._user = user

    def execute(self, query_data: QueryData) -> int:
        se = SearchEngineFactory().create()
        wrapper = _QueryWrapper()

        request = RequestFactory().get("/search/resources")

        if self._user:
            request.user = self._user
        else:
            request.user = User.objects.first()

        component = CrossModelAdvancedSearch()
        component.request = request

        querystring = JSONSerializer().serialize(query_data.to_dict())
        query_obj = {"query": wrapper}
        component.append_dsl(query_obj, querystring=querystring)

        response = se.search(
            index=RESOURCES_INDEX,
            body={"query": wrapper.dsl, "size": 0},
        )

        total = response.get("hits", {}).get("total", {})

        if isinstance(total, dict):
            return total.get("value", 0)

        return total or 0


class TestKeyGenerator:
    @staticmethod
    def generate(test_case: SnapshotCase, intersection_target: str) -> str:
        key_data = {
            "filters": [
                {
                    "card": f.card_name,
                    "graph": f.graph_name,
                    "node": f.node_name,
                    "value": f.value,
                }
                for f in sorted(
                    test_case.filters,
                    key=lambda x: (x.graph_name, x.card_name, x.node_name),
                )
            ],
            "target": intersection_target,
        }

        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode(), usedforsecurity=False).hexdigest()


class CrossModelSearchTestRunner:
    def __init__(self, user: Any = None) -> None:
        self.baseline_manager = BaselineManager()
        self.executor = SearchExecutor(user=user)
        self.query_builder = QueryBuilder()

    def _run_single_test(
        self,
        test_case: SnapshotCase,
        intersection_target: str,
        update_baselines: bool,
    ) -> TestResult:
        test_key = TestKeyGenerator.generate(test_case, intersection_target)

        query_data = self.query_builder.build(test_case, intersection_target)
        current_count = self.executor.execute(query_data)

        baseline_count = self.baseline_manager.get(test_key)
        passed = baseline_count is None or baseline_count == current_count

        if update_baselines:
            self.baseline_manager.update(test_key, current_count)

        return TestResult(
            baseline_count=baseline_count,
            current_count=current_count,
            intersection_target=intersection_target,
            passed=passed,
            test_name=test_case.name,
        )

    def run_tests(
        self,
        test_cases: list[SnapshotCase],
        update_baselines: bool = False,
    ) -> list[TestResult]:
        results = []

        for test_case in test_cases:
            targets = test_case.intersection_targets or (TranslateMode.NONE,)

            for target in targets:
                result = self._run_single_test(test_case, target, update_baselines)
                results.append(result)

        if update_baselines:
            self.baseline_manager.save()

        return results
