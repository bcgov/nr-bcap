from __future__ import annotations

import hashlib
import logging
import uuid

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import StrEnum
from typing_extensions import Any

from django.core.cache import cache
from django.db import close_old_connections
from django.db.models import Subquery

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models.models import (
    CardModel,
    CardXNodeXWidget,
    DDataType,
    GraphModel,
    Node,
    ResourceInstance,
    ResourceXResource,
    TileModel,
)
from arches.app.models.system_settings import settings
from arches.app.search.components.base import BaseSearchFilter
from arches.app.search.elasticsearch_dsl_builder import Bool, Nested, Terms
from arches.app.search.mappings import RESOURCES_INDEX
from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.utils.pagination import get_paginator


log = logging.getLogger(__name__)


details = {
    "classname": "CrossModelAdvancedSearch",
    "componentname": "cross-model-advanced-search",
    "componentpath": "views/components/search/cross-model-advanced-search",
    "config": {},
    "icon": "fa fa-search-plus",
    "modulename": "cross_model_advanced_search.py",
    "name": "Cross-Model Advanced Search",
    "searchcomponentid": "",
    "type": "cross-model-advanced-search-type",
}

# Cache timeout in seconds for search results and relationship graphs
BASE_CACHE_TIMEOUT = 300

# Number of resource IDs to process in a single database query to avoid memory issues
BATCH_SIZE = 5000

CACHE_TIMEOUT = BASE_CACHE_TIMEOUT
LINK_NODES_CACHE_KEY = "cross_model_link_nodes_{source}_{target}"
LINK_NODES_CACHE_TIMEOUT = BASE_CACHE_TIMEOUT

# Elasticsearch has a hard limit of 10,000 results per request without scrolling
MAX_ES_SIZE = 10000

# Maximum number of worker threads for parallel processing
MAX_WORKERS = 8

RELATIONSHIP_GRAPH_CACHE_KEY = "cross_model_search_relationship_graph"
RELATIONSHIP_GRAPH_CACHE_TIMEOUT = BASE_CACHE_TIMEOUT
RESOURCE_INSTANCE_NODES_CACHE_KEY = "cross_model_ri_nodes_{graph_id}"
RESOURCE_INSTANCE_NODES_CACHE_TIMEOUT = BASE_CACHE_TIMEOUT

# How long Elasticsearch keeps the search context alive between scroll requests
SCROLL_TIMEOUT = "2m"


class FilterOperator(StrEnum):
    NEQ = "neq"
    NOT = "not"
    NOT_EQ = "not_eq"
    NOT_EQUAL = "!="


class LogicalOperator(StrEnum):
    AND = "and"
    OR = "or"


class MatchType(StrEnum):
    ALL = "all"
    ANY = "any"


class ResourceInstanceDataType(StrEnum):
    RESOURCE_INSTANCE = "resource-instance"
    RESOURCE_INSTANCE_LIST = "resource-instance-list"


class TranslateMode(StrEnum):
    NONE = "none"


def bool_has_clause(bool_query: Bool) -> bool:
    dsl = bool_query.dsl["bool"]
    return bool(dsl.get("must") or dsl.get("should") or dsl.get("must_not"))


def chunked_iterable(iterable: list, size: int):
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


@dataclass
class FilterMatcher:
    """
    Handles matching tile data values against user-specified filter criteria.
    Supports both positive matching (value equals X) and inverted matching (value not equals X).
    Works with various data formats including concept URIs, list items, and primitive values.
    """

    inverted: bool = False
    value_to_match: set[str] = field(default_factory=set)

    def _check_positive_match(self, tile_value: Any) -> bool:
        if isinstance(tile_value, list):
            return any(self._matches_item(item) for item in tile_value)

        if isinstance(tile_value, str):
            return self._matches_string(tile_value)

        return any(str(v) == str(tile_value) for v in self.value_to_match)

    def _matches_dict_item(self, item: dict[str, Any]) -> bool:
        # Tile data stores references in various formats depending on datatype
        item_id = item.get("list_id") or item.get("id") or item.get("resourceId")
        item_uri = item.get("uri")

        for val in self.value_to_match:
            if item_id and str(val) in str(item_id):
                return True

            if item_uri and str(val) in str(item_uri):
                return True

        for label in item.get("labels", []):
            if isinstance(label, dict) and (list_item_id := label.get("list_item_id")):
                if any(str(val) in str(list_item_id) for val in self.value_to_match):
                    return True

        return False

    def _matches_item(self, item: Any) -> bool:
        if isinstance(item, dict):
            return self._matches_dict_item(item)

        return self._matches_string(str(item))

    def _matches_string(self, value: str) -> bool:
        return any(str(v).lower() in value.lower() for v in self.value_to_match)

    @classmethod
    def from_filter_value(cls, filter_value: Any) -> "FilterMatcher":
        if not isinstance(filter_value, dict):
            return cls()

        val = filter_value.get("val")
        op = filter_value.get("op", "")

        inverted = op in (
            FilterOperator.NOT,
            FilterOperator.NEQ,
            FilterOperator.NOT_EQUAL,
            FilterOperator.NOT_EQ,
        )

        if val is None:
            return cls(inverted=inverted)

        value_to_match = set()

        # Filter values can come in various formats: direct values, concept URIs,
        # or controlled list items with nested label structures
        for item in (val if isinstance(val, list) else [val]):
            if isinstance(item, dict):
                if uri := item.get("uri"):
                    value_to_match.add(uri)

                # Controlled list items store their ID in labels[0].list_item_id
                for label in item.get("labels", []):
                    if isinstance(label, dict) and (
                        list_item_id := label.get("list_item_id")
                    ):
                        value_to_match.add(list_item_id)
                        break
            else:
                value_to_match.add(str(item))

        return cls(inverted=inverted, value_to_match=value_to_match)

    def matches(self, tile_value: Any) -> bool:
        if not self.value_to_match:
            return False

        # Null tile values match only when using inverted (NOT) operators
        if tile_value is None:
            return self.inverted

        positive_match = self._check_positive_match(tile_value)

        if self.inverted:
            return not positive_match

        return positive_match


@dataclass
class NodeValue:
    """Wrapper for extracting resource instance IDs from tile data node values."""

    raw: Any

    def _iter_item(self) -> list[Any]:
        if self.raw is None:
            return []

        if isinstance(self.raw, list):
            return self.raw

        return [self.raw]

    def extract_resource_id(self) -> set[str]:
        """
        Extract referenced resource instance IDs from resource-instance or
        resource-instance-list datatype values.
        """

        result = set()

        for item in self._iter_item():
            if isinstance(item, dict) and "resourceId" in item:
                result.add(item["resourceId"])

        return result


@dataclass
class PaginationResult:
    current_page: int
    end_index: int
    has_next: bool
    has_other_pages: bool
    has_previous: bool
    next_page_number: int | None
    page_list: list[int]
    previous_page_number: int | None
    start_index: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_page": self.current_page,
            "end_index": self.end_index,
            "has_next": self.has_next,
            "has_other_pages": self.has_other_pages,
            "has_previous": self.has_previous,
            "next_page_number": self.next_page_number,
            "pages": self.page_list,
            "previous_page_number": self.previous_page_number,
            "start_index": self.start_index,
        }


@dataclass
class CardFilter:
    """Represents filter criteria for a single card (nodegroup) in the search."""

    node_filter: dict[str, Any] = field(default_factory=dict)
    nodegroup_id: str | None = None

    def _is_valid_filter(self, filter_value: Any) -> bool:
        if not filter_value:
            return False

        if isinstance(filter_value, dict):
            val = filter_value.get("val", "")
            # Allow explicit 0 or False values as valid filters
            return bool(val) or val == 0 or val is False

        return True

    def build_query(
        self,
        datatype_factory: DataTypeFactory,
        node_cache: dict[str, Node],
        request: Any,
    ) -> Bool:
        """
        Build an Elasticsearch Bool query from the card's node filters.
        Delegates to each node's datatype to construct the appropriate query syntax.
        """

        tile_query = Bool()

        for node_id, filter_value in self.node_filter.items():
            if not self._is_valid_filter(filter_value):
                continue

            node = node_cache.get(node_id)

            if not node:
                continue

            datatype = datatype_factory.get_instance(node.datatype)

            # Each datatype knows how to construct its own ES query filters
            if hasattr(datatype, "append_search_filters"):
                datatype.append_search_filters(filter_value, node, tile_query, request)

        return tile_query

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CardFilter":
        return cls(
            node_filter=data.get("filters", {}),
            nodegroup_id=data.get("nodegroup_id"),
        )


@dataclass
class GroupFilter:
    """
    Represents a group of card filters that can be combined with AND (match all)
    or OR (match any) logic.
    """

    card_list: list[CardFilter] = field(default_factory=list)
    match_type: MatchType = MatchType.ALL
    operator_after: LogicalOperator = LogicalOperator.AND

    def build_query(
        self,
        datatype_factory: DataTypeFactory,
        node_cache: dict[str, Node],
        request: Any,
    ) -> Bool:
        group_query = Bool()

        for card in self.card_list:
            tile_query = card.build_query(datatype_factory, node_cache, request)

            if not bool_has_clause(tile_query):
                continue

            # Wrap tile queries in Nested because tiles are stored as nested documents
            nested_query = Nested(path="tiles", query=tile_query)

            if self.match_type == MatchType.ANY:
                group_query.should(nested_query)
            else:
                group_query.must(nested_query)

        if group_query.dsl["bool"]["should"]:
            group_query.dsl["bool"]["minimum_should_match"] = 1

        return group_query

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GroupFilter":
        match_value = data.get("match", MatchType.ALL)
        operator_value = data.get("operator_after", LogicalOperator.AND)

        return cls(
            card_list=[CardFilter.from_dict(c) for c in data.get("cards", [])],
            match_type=MatchType(match_value) if match_value else MatchType.ALL,
            operator_after=(
                LogicalOperator(operator_value)
                if operator_value
                else LogicalOperator.AND
            ),
        )


@dataclass
class SectionFilter:
    """
    Represents all filter criteria for a single resource model.
    Contains multiple groups that can be combined with AND/OR operators.
    """

    graph_id: str | None = None
    group_list: list[GroupFilter] = field(default_factory=list)
    link_node_id: str | None = None
    linked_section_index: int | None = None

    def build_query(
        self,
        datatype_factory: DataTypeFactory,
        node_cache: dict[str, Node],
        request: Any,
    ) -> Bool:
        section_query = Bool()
        valid_groups = []

        for group in self.group_list:
            group_query = group.build_query(datatype_factory, node_cache, request)

            if bool_has_clause(group_query):
                valid_groups.append((group, group_query))

        if not valid_groups:
            return section_query

        if len(valid_groups) == 1:
            _, group_query = valid_groups[0]
            section_query.must(group_query)
            return section_query

        operators = [group.operator_after for group, _ in valid_groups[:-1]]
        all_and = all(op == LogicalOperator.AND for op in operators)
        all_or = all(op == LogicalOperator.OR for op in operators)

        if all_and:
            for _, group_query in valid_groups:
                section_query.must(group_query)

            return section_query

        if all_or:
            for _, group_query in valid_groups:
                section_query.should(group_query)

            section_query.dsl["bool"]["minimum_should_match"] = 1

            return section_query

        # Mixed operators: group consecutive ANDs together, then OR the AND-groups
        current_and_group = []
        or_groups = []

        for idx, (group, group_query) in enumerate(valid_groups):
            current_and_group.append(group_query)

            if idx < len(valid_groups) - 1 and operators[idx] == LogicalOperator.OR:
                or_groups.append(current_and_group)
                current_and_group = []

        if current_and_group:
            or_groups.append(current_and_group)

        for and_group in or_groups:
            if len(and_group) == 1:
                section_query.should(and_group[0])
            else:
                and_query = Bool()

                for q in and_group:
                    and_query.must(q)

                section_query.should(and_query)

        section_query.dsl["bool"]["minimum_should_match"] = 1

        return section_query

    def extract_node_filter(self) -> dict[str, Any]:
        """Flatten all node filters from all cards in this section into a single dict."""

        node_filter = {}

        for group in self.group_list:
            for card in group.card_list:
                for node_id, filter_value in card.node_filter.items():
                    if not filter_value:
                        continue

                    if isinstance(filter_value, dict):
                        val = filter_value.get("val")

                        if val or val == 0 or val is False:
                            node_filter[node_id] = filter_value
                    else:
                        node_filter[node_id] = filter_value

        return node_filter

    def extract_nodegroup_id(self) -> list[str]:
        return [
            card.nodegroup_id
            for group in self.group_list
            for card in group.card_list
            if card.nodegroup_id
        ]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SectionFilter":
        return cls(
            graph_id=data.get("graph_id"),
            group_list=[GroupFilter.from_dict(g) for g in data.get("groups", [])],
            link_node_id=data.get("link_node_id"),
            linked_section_index=data.get("linked_section_index"),
        )


@dataclass
class ElasticsearchScroller:
    """
    Handles scrolling through large Elasticsearch result sets that exceed the 10k limit.
    Uses the scroll API to maintain a consistent view of the index during iteration.
    """

    se: Any
    scroll_timeout: str = SCROLL_TIMEOUT
    size: int = MAX_ES_SIZE

    def _clear_scroll(self, scroll_id: str | None) -> None:
        """Release the scroll context to free resources."""

        if not scroll_id:
            return

        try:
            self.se.es.clear_scroll(scroll_id=scroll_id)
        except Exception:
            pass

    def scroll_id_only(self, query: dict[str, Any]) -> set[str]:
        """Scroll through results returning only document IDs."""

        resource_id = set()

        result = self.se.search(
            index=RESOURCES_INDEX,
            query=query,
            scroll=self.scroll_timeout,
            size=self.size,
            _source=False,
        )

        scroll_id = result.get("_scroll_id")

        for hit in result.get("hits", {}).get("hits", []):
            resource_id.add(hit["_id"])

        while result.get("hits", {}).get("hits", []):
            result = self.se.es.scroll(scroll_id=scroll_id, scroll=self.scroll_timeout)
            scroll_id = result.get("_scroll_id")

            for hit in result.get("hits", {}).get("hits", []):
                resource_id.add(hit["_id"])

        self._clear_scroll(scroll_id)

        return resource_id

    def scroll_with_source(
        self, query: dict[str, Any], source_field: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Scroll through results returning full documents or specified fields."""

        all_hit = []

        result = self.se.search(
            _source=source_field if source_field else True,
            index=RESOURCES_INDEX,
            query=query,
            scroll=self.scroll_timeout,
            size=self.size,
        )

        scroll_id = result.get("_scroll_id")
        all_hit.extend(result.get("hits", {}).get("hits", []))

        while result.get("hits", {}).get("hits", []):
            result = self.se.es.scroll(scroll_id=scroll_id, scroll=self.scroll_timeout)
            scroll_id = result.get("_scroll_id")
            all_hit.extend(result.get("hits", {}).get("hits", []))

        self._clear_scroll(scroll_id)

        return all_hit


class LinkNodeCache:
    """
    Singleton cache for resource-instance node configurations across all graphs.

    This cache tracks which graphs can link to which other graphs via resource-instance
    or resource-instance-list nodes. This information is used to determine how to
    traverse from one resource model to another during cross-model searches.

    Two types of nodes are tracked:
    - Constrained nodes: Have specific target graph IDs in their config
    - Unconstrained nodes: Can reference any graph (no graphid restriction in config)
    """

    _cache: dict[tuple[str, str], list[dict[str, Any]]] = {}
    _graph_ri_nodes: dict[str, list[dict[str, Any]]] = {}
    _initialized: bool = False
    _unconstrained_nodes: dict[str, list[dict[str, Any]]] = {}

    @classmethod
    def _extract_graph_id_from_config(cls, config: dict[str, Any]) -> list[str]:
        """
        Extract target graph IDs from a resource-instance node's config.
        Handles both legacy format (graphid) and new format (graphs array).
        """

        graph_id = []

        if "graphid" in config:
            graphid_val = config.get("graphid")

            if graphid_val:
                if isinstance(graphid_val, list):
                    graph_id.extend(graphid_val)
                else:
                    graph_id.append(graphid_val)

        if "graphs" in config:
            for g in config.get("graphs", []):
                if isinstance(g, dict) and g.get("graphid"):
                    graph_id.append(g["graphid"])

        return [str(g) for g in graph_id]

    @classmethod
    def _initialize(cls) -> None:
        """Load all resource-instance nodes from the database and categorize them."""

        node_queryset = Node.objects.filter(
            datatype__in=[
                ResourceInstanceDataType.RESOURCE_INSTANCE,
                ResourceInstanceDataType.RESOURCE_INSTANCE_LIST,
            ],
        ).values("config", "graph_id", "nodegroup_id", "nodeid")

        for node in node_queryset:
            graph_id = str(node["graph_id"])
            target_graph_ids = cls._extract_graph_id_from_config(node["config"] or {})

            node_info = {
                "node_id": str(node["nodeid"]),
                "nodegroup_id": str(node["nodegroup_id"]),
                "target_graph_ids": set(target_graph_ids),
            }

            if graph_id not in cls._graph_ri_nodes:
                cls._graph_ri_nodes[graph_id] = []

            if target_graph_ids:
                cls._graph_ri_nodes[graph_id].append(node_info)
            else:
                # Nodes without target constraints can reference any graph
                if graph_id not in cls._unconstrained_nodes:
                    cls._unconstrained_nodes[graph_id] = []

                cls._unconstrained_nodes[graph_id].append(node_info)

        cls._initialized = True

    @classmethod
    def clear(cls) -> None:
        cls._cache.clear()
        cls._graph_ri_nodes.clear()
        cls._initialized = False
        cls._unconstrained_nodes.clear()

    @classmethod
    def get_link_nodes(
        cls, source_graph_id: str, target_graph_id: str
    ) -> list[dict[str, Any]]:
        """
        Get all nodes in source_graph that can reference resources in target_graph.
        Returns both explicitly constrained nodes and unconstrained nodes.
        """

        if not cls._initialized:
            cls._initialize()

        cache_key = (source_graph_id, target_graph_id)

        if cache_key in cls._cache:
            return cls._cache[cache_key]

        result = []
        source_nodes = cls._graph_ri_nodes.get(source_graph_id, [])

        for node_info in source_nodes:
            if target_graph_id in node_info["target_graph_ids"]:
                result.append(
                    {
                        "node_id": node_info["node_id"],
                        "nodegroup_id": node_info["nodegroup_id"],
                    }
                )

        # Unconstrained nodes can link to any graph
        unconstrained = cls._unconstrained_nodes.get(source_graph_id, [])

        for node_info in unconstrained:
            result.append(
                {
                    "node_id": node_info["node_id"],
                    "nodegroup_id": node_info["nodegroup_id"],
                }
            )

        cls._cache[cache_key] = result
        return result

    @classmethod
    def get_ri_nodes_for_graph(cls, graph_id: str) -> list[dict[str, Any]]:
        if not cls._initialized:
            cls._initialize()

        return cls._graph_ri_nodes.get(graph_id, [])


class CrossModelAdvancedSearch(BaseSearchFilter):
    """
    Search filter that enables queries spanning multiple resource models.

    This filter supports two modes:
    1. Raw mode (translate_mode="none"): Returns resources matching filters from any
       of the specified models, combined with OR logic.
    2. Intersection mode (translate_mode=<graph_slug>): Finds resources matching
       filters in source models, then translates results to a target model by
       following resource-to-resource relationships.

    The intersection logic works by:
    1. Running ES queries to find matching resources in each source model
    2. Traversing ResourceXResource relationships and tile-based resource-instance
       links to find connected resources in the target model
    3. Computing the intersection of target resources across all source filters
    """

    _node_cache: dict[str, Node] = {}
    _query_data = None

    def _add_permission_property(self, hit_list: list[dict[str, Any]]) -> None:
        """Add permission flags to each hit based on the current user's access rights."""

        user = self.request.user

        resource_ids = [
            hit.get("_id") or hit.get("_source", {}).get("resourceinstanceid")
            for hit in hit_list
        ]

        resource_ids = [rid for rid in resource_ids if rid]

        perm_cache = {}

        for rid in resource_ids:
            perm_cache[rid] = {
                "can_edit": user.has_perm("change_resourceinstance", rid),
                "can_read": user.has_perm("view_resourceinstance", rid),
            }

        for hit in hit_list:
            resource_id = hit.get("_id") or hit.get("_source", {}).get(
                "resourceinstanceid"
            )

            if not resource_id or resource_id not in perm_cache:
                hit["can_edit"] = False
                hit["can_read"] = False
                hit["is_principal"] = False

                continue

            perms = perm_cache[resource_id]
            hit["can_edit"] = perms["can_edit"]
            hit["can_read"] = perms["can_read"]
            hit["is_principal"] = perms["can_read"]

    def _apply_linked_section_filter(
        self,
        primary_section: SectionFilter,
        linked_section: SectionFilter,
        primary_resource_id: set[str],
    ) -> set[str]:
        """
        Filter primary resources by checking if their linked resources match
        the linked section's criteria.

        This handles cases where sections from different models are related via
        resource-instance nodes (e.g., Site Visit -> Archaeological Site).
        """

        if not primary_resource_id:
            return set()

        linked_graph_id = linked_section.graph_id

        if not linked_graph_id:
            return primary_resource_id

        link_node_info = LinkNodeCache.get_link_nodes(
            primary_section.graph_id, linked_graph_id
        )

        if not link_node_info:
            return primary_resource_id

        linked_node_filter = linked_section.extract_node_filter()

        if not linked_node_filter:
            return primary_resource_id

        primary_nodegroup_id = [info["nodegroup_id"] for info in link_node_info]
        link_node_id_set = {info["node_id"] for info in link_node_info}

        primary_id_list = list(primary_resource_id)
        chunks = list(chunked_iterable(primary_id_list, BATCH_SIZE))

        def process_primary_chunk(chunk: list[str]) -> dict[str, set[str]]:
            close_old_connections()

            chunk_mapping = defaultdict(set)

            tile_queryset = (
                TileModel.objects.filter(
                    resourceinstance_id__in=chunk,
                    nodegroup_id__in=primary_nodegroup_id,
                )
                .values("data", "resourceinstance_id")
                .iterator(chunk_size=2000)
            )

            for tile in tile_queryset:
                tiledata = tile.get("data") or {}
                primary_id = str(tile.get("resourceinstance_id"))

                for node_id in link_node_id_set:
                    if node_id not in tiledata:
                        continue

                    node_value = NodeValue(raw=tiledata.get(node_id))
                    linked_ids = node_value.extract_resource_id()

                    if linked_ids:
                        chunk_mapping[primary_id].update(linked_ids)

            return dict(chunk_mapping)

        # Build a mapping of primary resources to their linked resources
        primary_to_linked_mapping = defaultdict(set)

        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(chunks))) as executor:
            futures = [
                executor.submit(process_primary_chunk, chunk) for chunk in chunks
            ]

            for future in as_completed(futures):
                chunk_result = future.result()

                for primary_id, linked_ids in chunk_result.items():
                    primary_to_linked_mapping[primary_id].update(linked_ids)

        if not primary_to_linked_mapping:
            return set()

        all_linked_id = set()

        for linked_ids in primary_to_linked_mapping.values():
            all_linked_id.update(linked_ids)

        # Check which linked resources match the filter criteria
        linked_nodegroup_id = linked_section.extract_nodegroup_id()
        all_linked_id_list = list(all_linked_id)
        linked_chunks = list(chunked_iterable(all_linked_id_list, BATCH_SIZE))

        def process_linked_chunk(chunk: list[str]) -> set[str]:
            close_old_connections()

            matching = set()

            linked_tile_queryset = (
                TileModel.objects.filter(
                    resourceinstance_id__in=chunk,
                    nodegroup_id__in=linked_nodegroup_id,
                )
                .values("data", "resourceinstance_id")
                .iterator(chunk_size=2000)
            )

            for tile in linked_tile_queryset:
                tiledata = tile.get("data") or {}
                linked_id = str(tile.get("resourceinstance_id"))

                if self._tile_matches_node_filter(tiledata, linked_node_filter):
                    matching.add(linked_id)

            return matching

        matching_linked_id = set()

        with ThreadPoolExecutor(
            max_workers=min(MAX_WORKERS, len(linked_chunks))
        ) as executor:
            futures = [
                executor.submit(process_linked_chunk, chunk) for chunk in linked_chunks
            ]

            for future in as_completed(futures):
                matching_linked_id.update(future.result())

        # Return only primary resources that link to matching linked resources
        result = set()

        for primary_id, linked_ids in primary_to_linked_mapping.items():
            if linked_ids & matching_linked_id:
                result.add(primary_id)

        return result

    def _build_node_cache(self, section_data_list: list[dict[str, Any]]) -> None:
        """Preload all nodes referenced in filters to avoid repeated database queries."""

        node_ids = set()

        for section_data in section_data_list:
            for group_data in section_data.get("groups", []):
                for card_data in group_data.get("cards", []):
                    node_ids.update(card_data.get("filters", {}).keys())

        if not node_ids:
            return

        nodes = Node.objects.filter(pk__in=node_ids).select_related("nodegroup")

        for node in nodes:
            self._node_cache[str(node.nodeid)] = node

    def _compute_combined_target_id(
        self,
        section_data_list: list[dict[str, Any]],
        target_graph_id: str,
        strict_mode: bool,
    ) -> set[str]:
        """
        Compute the intersection of target resources from all sections.
        Each section produces a set of target resources; the final result
        is the intersection of all these sets.
        """

        datatype_factory = DataTypeFactory()
        se = SearchEngineFactory().create()
        scroller = ElasticsearchScroller(se=se)

        section_list = [SectionFilter.from_dict(s) for s in section_data_list]

        # Group sections by graph to handle multiple sections from the same model
        section_by_graph = defaultdict(list)

        for idx, section in enumerate(section_list):
            if section.graph_id:
                section_by_graph[section.graph_id].append((idx, section))

        def process_graph_sections(
            graph_id: str,
            sections: list[tuple[int, SectionFilter]],
        ) -> set[str] | None:
            close_old_connections()

            primary_idx, primary_section = sections[0]

            resource_id = self._get_resource_id_for_section(
                primary_section, datatype_factory, scroller
            )

            if not resource_id:
                return None

            # Apply linked section filters if any
            for linked_idx, linked_section in sections[1:]:
                if linked_section.linked_section_index == primary_idx:
                    resource_id = self._apply_linked_section_filter(
                        primary_section,
                        linked_section,
                        resource_id,
                    )

            target_id = self._get_target_id_for_resource(
                resource_id,
                graph_id,
                target_graph_id,
                section=primary_section,
                strict_mode=strict_mode,
            )

            return target_id

        combined_target_id = None
        graph_items = list(section_by_graph.items())

        with ThreadPoolExecutor(
            max_workers=min(MAX_WORKERS, len(graph_items))
        ) as executor:
            future_to_graph = {
                executor.submit(process_graph_sections, graph_id, sections): graph_id
                for graph_id, sections in graph_items
            }

            for future in as_completed(future_to_graph):
                target_id = future.result()

                # Intersection: all sections must contribute matching targets
                if target_id is None:
                    return set()

                if combined_target_id is None:
                    combined_target_id = target_id
                else:
                    combined_target_id &= target_id

        processed_graph_id = set(section_by_graph.keys())

        remaining_sections = [
            SectionFilter.from_dict(s)
            for s in section_data_list
            if SectionFilter.from_dict(s).graph_id not in processed_graph_id
            and SectionFilter.from_dict(s).linked_section_index is None
        ]

        if remaining_sections:

            def process_remaining_section(section: SectionFilter) -> set[str] | None:
                close_old_connections()

                resource_id = self._get_resource_id_for_section(
                    section, datatype_factory, scroller
                )

                if not resource_id:
                    return None

                return self._get_target_id_for_resource(
                    resource_id,
                    section.graph_id,
                    target_graph_id,
                    section=section,
                    strict_mode=strict_mode,
                )

            with ThreadPoolExecutor(
                max_workers=min(MAX_WORKERS, len(remaining_sections))
            ) as executor:
                future_to_section = {
                    executor.submit(process_remaining_section, section): section
                    for section in remaining_sections
                }

                for future in as_completed(future_to_section):
                    target_id = future.result()

                    if target_id is None:
                        return set()

                    if combined_target_id is None:
                        combined_target_id = target_id
                    else:
                        combined_target_id &= target_id

        return combined_target_id or set()

    def _compute_combined_target_id_with_relational_filter(
        self,
        section_data_list: list[dict[str, Any]],
        target_graph_id: str,
        strict_mode: bool,
    ) -> set[str]:
        """
        Compute target IDs while respecting relational constraints between sections.
        Handles sections that are linked via resource-instance nodes.
        """

        datatype_factory = DataTypeFactory()
        se = SearchEngineFactory().create()
        scroller = ElasticsearchScroller(se=se)

        section_list = [SectionFilter.from_dict(s) for s in section_data_list]

        # Separate primary sections from those linked to other sections
        primary_section_list = []
        linked_section_map = defaultdict(list)

        for idx, section in enumerate(section_list):
            if section.linked_section_index is not None:
                linked_section_map[section.linked_section_index].append(section)
            else:
                primary_section_list.append((idx, section))

        combined_target_id = None

        for idx, primary_section in primary_section_list:
            resource_id = self._get_resource_id_for_section(
                primary_section, datatype_factory, scroller
            )

            if not resource_id:
                return set()

            # Apply all filters from sections linked to this primary section
            if idx in linked_section_map:
                for linked_section in linked_section_map[idx]:
                    resource_id = self._apply_linked_section_filter(
                        primary_section,
                        linked_section,
                        resource_id,
                    )

                    if not resource_id:
                        return set()

            target_id = self._get_target_id_for_resource(
                resource_id,
                primary_section.graph_id,
                target_graph_id,
                section=primary_section,
                strict_mode=strict_mode,
            )

            if combined_target_id is None:
                combined_target_id = target_id
            else:
                combined_target_id &= target_id

        # Handle linked sections that filter the target graph directly
        for idx, section in enumerate(section_list):
            if section.linked_section_index is None:
                continue

            if section.graph_id == target_graph_id:
                # Direct filter on target graph - just intersect with ES results
                direct_match_id = self._get_resource_id_for_section(
                    section, datatype_factory, scroller
                )

                if not direct_match_id:
                    return set()

                if combined_target_id is None:
                    combined_target_id = direct_match_id
                else:
                    combined_target_id &= direct_match_id

            else:
                # Linked section on different graph - find targets connected to matching linked resources
                linked_match_id = self._get_resource_id_for_section(
                    section, datatype_factory, scroller
                )

                if not linked_match_id:
                    return set()

                connected_target_id = self._get_target_resources_connected_to(
                    combined_target_id,
                    target_graph_id,
                    linked_match_id,
                    section.graph_id,
                )

                if not connected_target_id:
                    return set()

                combined_target_id &= connected_target_id

        return combined_target_id or set()

    def _detect_section_linkage(
        self, section_data_list: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Automatically detect relationships between sections based on resource-instance
        node configurations. If section A can link to section B's graph via a
        resource-instance node, mark B as linked to A.
        """

        section_list = [SectionFilter.from_dict(s) for s in section_data_list]

        for idx, section in enumerate(section_list):
            if section.linked_section_index is not None:
                continue

            for other_idx, other_section in enumerate(section_list):
                if idx == other_idx:
                    continue

                if other_section.linked_section_index is not None:
                    continue

                link_nodes = LinkNodeCache.get_link_nodes(
                    section.graph_id, other_section.graph_id
                )

                if link_nodes:
                    section_data_list[other_idx]["linked_section_index"] = idx
                    section_data_list[other_idx]["link_node_id"] = link_nodes[0][
                        "node_id"
                    ]

        return section_data_list

    def _extract_target_id_from_tile_strict(
        self,
        source_resource_id: set[str],
        section: SectionFilter,
        target_graph_id: str,
    ) -> set[str]:
        """
        In strict mode, only return target resources that are directly linked
        from tiles that also match the filter criteria. This ensures the filter
        applies to the same tile containing the link.
        """

        if not source_resource_id:
            return set()

        forward_link_nodes = LinkNodeCache.get_link_nodes(
            section.graph_id, target_graph_id
        )
        reverse_link_nodes = LinkNodeCache.get_link_nodes(
            target_graph_id, section.graph_id
        )

        if not forward_link_nodes and not reverse_link_nodes:
            return set()

        node_filter = section.extract_node_filter()
        nodegroup_id = section.extract_nodegroup_id()

        def process_forward_strict() -> set[str]:
            close_old_connections()

            result = set()

            if not forward_link_nodes:
                return result

            resource_instance_node_id = {info["node_id"] for info in forward_link_nodes}
            source_id_list = list(source_resource_id)

            for chunk in chunked_iterable(source_id_list, BATCH_SIZE):
                tile_queryset = (
                    TileModel.objects.filter(
                        nodegroup_id__in=nodegroup_id,
                        resourceinstance_id__in=chunk,
                    )
                    .values("data")
                    .iterator(chunk_size=2000)
                )

                for tile in tile_queryset:
                    tiledata = tile.get("data") or {}

                    if not self._tile_matches_node_filter(tiledata, node_filter):
                        continue

                    for node_id in resource_instance_node_id:
                        if node_id not in tiledata:
                            continue

                        node_value = NodeValue(raw=tiledata.get(node_id))
                        result.update(node_value.extract_resource_id())

            return result

        def process_reverse_strict() -> set[str]:
            close_old_connections()

            result = set()

            if not reverse_link_nodes:
                return result

            reverse_node_id_set = {info["node_id"] for info in reverse_link_nodes}
            reverse_nodegroup_id_set = {
                info["nodegroup_id"] for info in reverse_link_nodes
            }

            tile_queryset = (
                TileModel.objects.filter(
                    nodegroup_id__in=reverse_nodegroup_id_set,
                    resourceinstance__graph_id=target_graph_id,
                )
                .values("data", "resourceinstance_id")
                .iterator(chunk_size=2000)
            )

            for tile in tile_queryset:
                tiledata = tile.get("data") or {}
                target_resource_id = str(tile.get("resourceinstance_id"))

                for node_id in reverse_node_id_set:
                    if node_id not in tiledata:
                        continue

                    node_value = NodeValue(raw=tiledata.get(node_id))
                    referenced_ids = node_value.extract_resource_id()

                    if referenced_ids & source_resource_id:
                        result.add(target_resource_id)
                        break

            return result

        target_id = set()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(process_forward_strict),
                executor.submit(process_reverse_strict),
            ]

            for future in as_completed(futures):
                target_id.update(future.result())

        if target_id:
            verified_target_id = set()
            target_id_list = list(target_id)

            for chunk in chunked_iterable(target_id_list, BATCH_SIZE):
                verified_ids = ResourceInstance.objects.filter(
                    graph_id=target_graph_id,
                    resourceinstanceid__in=chunk,
                ).values_list("resourceinstanceid", flat=True)

                verified_target_id.update(str(rid) for rid in verified_ids)

            return verified_target_id

        return target_id

    def _get_cache_key(self, raw_data: dict[str, Any]) -> str:
        """Generate a unique cache key for the search parameters."""

        cache_data = {
            "sections": raw_data.get("sections", []),
            "strict_mode": raw_data.get("strict_mode", False),
            "translate_mode": raw_data.get("translate_mode", TranslateMode.NONE),
            "user_id": self.request.user.id,
        }

        return f"cross_model_search_{hashlib.md5(str(cache_data).encode()).hexdigest()}"

    def _get_graph_id(self, slug_or_id: str) -> str | None:
        """Resolve a graph slug or UUID string to a graph ID."""

        try:
            uuid.UUID(slug_or_id)
            graph = (
                GraphModel.objects.filter(graphid=slug_or_id).only("graphid").first()
            )
        except ValueError:
            graph = GraphModel.objects.filter(slug=slug_or_id).only("graphid").first()

        return str(graph.graphid) if graph else None

    def _get_intersection_target(self) -> list[dict[str, Any]]:
        """
        Build the list of available intersection targets for the UI.
        Graphs are sorted alphabetically by name.
        """

        if not LinkNodeCache._initialized:
            LinkNodeCache._initialize()

        graph_queryset = (
            GraphModel.objects.filter(
                is_active=True,
                isresource=True,
            )
            .exclude(pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
            .exclude(
                source_identifier__isnull=False,
            )
            .only("graphid", "name", "slug")
        )

        target = []

        for graph in graph_queryset:
            graph_id = str(graph.graphid)
            graph_name = graph.name

            if isinstance(graph_name, dict):
                graph_name = graph_name.get(
                    "en", list(graph_name.values())[0] if graph_name else graph.slug
                )

            target.append(
                {
                    "graph_id": graph_id,
                    "label": f"Intersect to {graph_name}",
                    "name": graph_name,
                    "slug": graph.slug,
                }
            )

        target.sort(key=lambda x: (x["name"] or "").lower())

        return target

    def _get_pagination_param(self, total: int | None = None) -> tuple[int, int, int]:
        page_param = (
            self.request.GET.get("paging-filter")
            or self.request.POST.get("paging-filter")
            or "1"
        )

        try:
            page = int(page_param) if page_param else 1
        except (TypeError, ValueError):
            page = 1

        per_page = settings.SEARCH_ITEMS_PER_PAGE

        if total is not None and total > 0:
            max_page = (total + per_page - 1) // per_page
            page = min(page, max_page)

        if total == 0:
            page = 1

        page = max(1, page)
        start = per_page * (page - 1)

        return page, per_page, start

    def _get_pagination_result(
        self, response_object: dict[str, Any], total: int, page: int
    ) -> PaginationResult:
        paginator, page_list = get_paginator(
            self.request,
            response_object["results"],
            total,
            page,
            settings.SEARCH_ITEMS_PER_PAGE,
        )

        page_obj = paginator.page(page)

        return PaginationResult(
            current_page=page_obj.number,
            end_index=page_obj.end_index(),
            has_next=page_obj.has_next(),
            has_other_pages=page_obj.has_other_pages(),
            has_previous=page_obj.has_previous(),
            next_page_number=(
                page_obj.next_page_number() if page_obj.has_next() else None
            ),
            page_list=page_list,
            previous_page_number=(
                page_obj.previous_page_number() if page_obj.has_previous() else None
            ),
            start_index=page_obj.start_index(),
        )

    def _get_related_via_rxr_bfs(
        self,
        source_resource_id: set[str],
        target_graph_id: str,
        max_hops: int = 3,
    ) -> set[str]:
        """
        Find target resources connected via ResourceXResource using BFS.
        Uses Subquery to let PostgreSQL handle intermediate ID sets internally.
        Uses ThreadPoolExecutor to parallelize queries for better performance.
        """

        if not source_resource_id:
            return set()

        source_list = list(source_resource_id)
        target_uuid = uuid.UUID(target_graph_id)
        all_targets = set()
        current_subqueries = [source_list]

        def query_forward_targets(filter_arg):
            close_old_connections()

            if isinstance(filter_arg, list):
                return set(
                    ResourceXResource.objects.filter(
                        from_resource_id__in=filter_arg,
                        to_resource_graph_id=target_uuid,
                    ).values_list("to_resource_id", flat=True)
                )

            return set(
                ResourceXResource.objects.filter(
                    from_resource_id__in=Subquery(filter_arg),
                    to_resource_graph_id=target_uuid,
                ).values_list("to_resource_id", flat=True)
            )

        def query_reverse_targets(filter_arg):
            close_old_connections()

            if isinstance(filter_arg, list):
                return set(
                    ResourceXResource.objects.filter(
                        to_resource_id__in=filter_arg,
                        from_resource_graph_id=target_uuid,
                    ).values_list("from_resource_id", flat=True)
                )

            return set(
                ResourceXResource.objects.filter(
                    to_resource_id__in=Subquery(filter_arg),
                    from_resource_graph_id=target_uuid,
                ).values_list("from_resource_id", flat=True)
            )

        for hop in range(max_hops):
            hop_targets = set()
            next_subqueries = []

            with ThreadPoolExecutor(
                max_workers=min(MAX_WORKERS, len(current_subqueries) * 2)
            ) as executor:
                futures = []

                for subq in current_subqueries:
                    futures.append(executor.submit(query_forward_targets, subq))
                    futures.append(executor.submit(query_reverse_targets, subq))

                for future in as_completed(futures):
                    hop_targets.update(future.result())

            all_targets.update(str(rid) for rid in hop_targets)

            if hop < max_hops - 1:
                for subq in current_subqueries:
                    if isinstance(subq, list):
                        filter_arg = subq
                    else:
                        filter_arg = Subquery(subq)

                    forward_intermediate = (
                        ResourceXResource.objects.filter(
                            from_resource_id__in=filter_arg,
                        )
                        .exclude(
                            to_resource_graph_id=target_uuid,
                        )
                        .values("to_resource_id")
                    )

                    reverse_intermediate = (
                        ResourceXResource.objects.filter(
                            to_resource_id__in=filter_arg,
                        )
                        .exclude(
                            from_resource_graph_id=target_uuid,
                        )
                        .values("from_resource_id")
                    )

                    next_subqueries.append(forward_intermediate)
                    next_subqueries.append(reverse_intermediate)

            current_subqueries = next_subqueries

            if not current_subqueries:
                break

        return all_targets

    def _get_resource_id_for_section(
        self,
        section: SectionFilter,
        datatype_factory: DataTypeFactory,
        scroller: ElasticsearchScroller,
    ) -> set[str]:
        """Run the ES query for a section and return all matching resource IDs."""

        if not section.graph_id:
            return set()

        section_query = section.build_query(
            datatype_factory, self._node_cache, self.request
        )

        if not bool_has_clause(section_query):
            return set()

        full_query = Bool()
        full_query.filter(Terms(field="graph_id", terms=[section.graph_id]))
        full_query.must(section_query)

        return scroller.scroll_id_only(full_query.dsl)

    def _get_resources_referencing(
        self,
        resource_id: set[str],
        resource_graph_id: str,
    ) -> dict[str, set[str]]:
        """
        Find all resources that reference the given resources via ResourceXResource.
        Returns a dict mapping graph_id -> set of referencing resource IDs.
        """

        if not resource_id:
            return {}

        result = defaultdict(set)
        resource_id_list = list(resource_id)

        forward_refs = (
            ResourceXResource.objects.filter(
                to_resource_id__in=resource_id_list,
            )
            .exclude(
                from_resource_graph_id=resource_graph_id,
            )
            .values_list("from_resource_id", "from_resource_graph_id")
        )

        for from_id, from_graph in forward_refs:
            if from_graph:
                result[str(from_graph)].add(str(from_id))

        reverse_refs = (
            ResourceXResource.objects.filter(
                from_resource_id__in=resource_id_list,
            )
            .exclude(
                to_resource_graph_id=resource_graph_id,
            )
            .values_list("to_resource_id", "to_resource_graph_id")
        )

        for to_id, to_graph in reverse_refs:
            if to_graph:
                result[str(to_graph)].add(str(to_id))

        return dict(result)

    def _get_target_id_for_resource(
        self,
        resource_id: set[str],
        source_graph_id: str,
        target_graph_id: str,
        section: SectionFilter | None = None,
        strict_mode: bool = False,
    ) -> set[str]:
        """
        Find all target graph resources connected to the given source resources.
        Uses both ResourceXResource and tile-based resource-instance links.
        """

        if not resource_id:
            return set()

        if source_graph_id == target_graph_id:
            return resource_id

        if strict_mode and section:
            return self._extract_target_id_from_tile_strict(
                resource_id, section, target_graph_id
            )

        tile_target_id = self._get_target_id_from_direct_tiles(
            resource_id, source_graph_id, target_graph_id
        )

        if tile_target_id:
            return tile_target_id

        tile_target_id = self._get_target_id_via_tile_bfs(
            resource_id, source_graph_id, target_graph_id
        )

        if tile_target_id:
            return tile_target_id

        rxr_target_id = self._get_related_via_rxr_bfs(resource_id, target_graph_id)

        return rxr_target_id

    def _get_target_id_via_tile_bfs(
        self,
        source_resource_id: set[str],
        source_graph_id: str,
        target_graph_id: str,
        max_hops: int = 3,
    ) -> set[str]:
        """
        Find target resources connected via multi-hop relationships.
        Uses RXR where available, falls back to tiles otherwise.
        Traverses both forward and reverse directions.
        """

        if not source_resource_id:
            return set()

        if source_graph_id == target_graph_id:
            return source_resource_id

        visited_resource_id = set(source_resource_id)
        current_frontier = set(source_resource_id)
        target_id = set()

        for _ in range(max_hops):
            if not current_frontier:
                break

            next_frontier = set()
            frontier_list = list(current_frontier)

            for chunk in chunked_iterable(frontier_list, BATCH_SIZE):
                forward_refs = ResourceXResource.objects.filter(
                    from_resource_id__in=chunk,
                ).values_list("to_resource_id", "to_resource_graph_id")

                for to_id, to_graph in forward_refs:
                    to_id_str = str(to_id)

                    if to_id_str in visited_resource_id:
                        continue

                    if str(to_graph) == target_graph_id:
                        target_id.add(to_id_str)
                    else:
                        next_frontier.add(to_id_str)

                reverse_refs = ResourceXResource.objects.filter(
                    to_resource_id__in=chunk,
                ).values_list("from_resource_id", "from_resource_graph_id")

                for from_id, from_graph in reverse_refs:
                    from_id_str = str(from_id)

                    if from_id_str in visited_resource_id:
                        continue

                    if str(from_graph) == target_graph_id:
                        target_id.add(from_id_str)
                    else:
                        next_frontier.add(from_id_str)

            frontier_graph_ids = set(
                str(gid)
                for gid in ResourceInstance.objects.filter(
                    resourceinstanceid__in=frontier_list[:1000],
                )
                .values_list("graph_id", flat=True)
                .distinct()
            )

            for frontier_graph_id in frontier_graph_ids:
                rxr_forward_exists = ResourceXResource.objects.filter(
                    from_resource_graph_id=frontier_graph_id,
                ).exists()

                if rxr_forward_exists:
                    continue

                ri_nodes = LinkNodeCache.get_ri_nodes_for_graph(frontier_graph_id)

                if not ri_nodes:
                    continue

                nodegroup_id_set = {info["nodegroup_id"] for info in ri_nodes}
                node_id_set = {info["node_id"] for info in ri_nodes}

                frontier_in_graph = [
                    rid for rid in frontier_list if rid in current_frontier
                ]

                for chunk in chunked_iterable(frontier_in_graph, BATCH_SIZE):
                    tile_queryset = (
                        TileModel.objects.filter(
                            nodegroup_id__in=nodegroup_id_set,
                            resourceinstance_id__in=chunk,
                        )
                        .values("data")
                        .iterator(chunk_size=2000)
                    )

                    for tile in tile_queryset:
                        tiledata = tile.get("data") or {}

                        for node_id in node_id_set:
                            if node_id not in tiledata:
                                continue

                            node_value = NodeValue(raw=tiledata.get(node_id))
                            referenced_ids = node_value.extract_resource_id()

                            for ref_id in referenced_ids:
                                if ref_id in visited_resource_id:
                                    continue

                                next_frontier.add(ref_id)

            if not next_frontier:
                break

            next_frontier_list = list(next_frontier)

            for chunk in chunked_iterable(next_frontier_list, BATCH_SIZE):
                matching_targets = ResourceInstance.objects.filter(
                    graph_id=target_graph_id,
                    resourceinstanceid__in=chunk,
                ).values_list("resourceinstanceid", flat=True)

                target_id.update(str(rid) for rid in matching_targets)

            visited_resource_id.update(next_frontier)
            current_frontier = next_frontier - target_id

        return target_id

    def _get_target_id_from_direct_tiles(
        self,
        source_resource_id: set[str],
        source_graph_id: str,
        target_graph_id: str,
    ) -> set[str]:
        """
        Find target resources directly linked via resource-instance nodes.
        Tries RXR first, falls back to tiles if no RXR relationships exist.
        """

        if not source_resource_id:
            return set()

        forward_link_nodes = LinkNodeCache.get_link_nodes(
            source_graph_id, target_graph_id
        )
        reverse_link_nodes = LinkNodeCache.get_link_nodes(
            target_graph_id, source_graph_id
        )

        if not forward_link_nodes and not reverse_link_nodes:
            return set()

        target_id = set()
        source_id_list = list(source_resource_id)

        rxr_has_forward = False
        rxr_has_reverse = False

        if forward_link_nodes:
            rxr_has_forward = ResourceXResource.objects.filter(
                from_resource_graph_id=source_graph_id,
                to_resource_graph_id=target_graph_id,
            ).exists()

        if reverse_link_nodes:
            rxr_has_reverse = ResourceXResource.objects.filter(
                to_resource_graph_id=source_graph_id,
                from_resource_graph_id=target_graph_id,
            ).exists()

        if forward_link_nodes:
            if rxr_has_forward:
                for chunk in chunked_iterable(source_id_list, BATCH_SIZE):
                    forward_targets = ResourceXResource.objects.filter(
                        from_resource_id__in=chunk,
                        to_resource_graph_id=target_graph_id,
                    ).values_list("to_resource_id", flat=True)

                    target_id.update(str(rid) for rid in forward_targets)
            else:
                nodegroup_id_set = {info["nodegroup_id"] for info in forward_link_nodes}
                node_id_set = {info["node_id"] for info in forward_link_nodes}

                for chunk in chunked_iterable(source_id_list, BATCH_SIZE):
                    tile_queryset = (
                        TileModel.objects.filter(
                            nodegroup_id__in=nodegroup_id_set,
                            resourceinstance_id__in=chunk,
                        )
                        .values("data")
                        .iterator(chunk_size=2000)
                    )

                    for tile in tile_queryset:
                        tiledata = tile.get("data") or {}

                        for node_id in node_id_set:
                            if node_id not in tiledata:
                                continue

                            node_value = NodeValue(raw=tiledata.get(node_id))
                            target_id.update(node_value.extract_resource_id())

        if reverse_link_nodes:
            if rxr_has_reverse:
                for chunk in chunked_iterable(source_id_list, BATCH_SIZE):
                    reverse_targets = ResourceXResource.objects.filter(
                        to_resource_id__in=chunk,
                        from_resource_graph_id=target_graph_id,
                    ).values_list("from_resource_id", flat=True)

                    target_id.update(str(rid) for rid in reverse_targets)
            else:
                nodegroup_id_set = {info["nodegroup_id"] for info in reverse_link_nodes}
                node_id_set = {info["node_id"] for info in reverse_link_nodes}

                for chunk in chunked_iterable(source_id_list, BATCH_SIZE):
                    tile_queryset = (
                        TileModel.objects.filter(
                            nodegroup_id__in=nodegroup_id_set,
                            resourceinstance__graph_id=target_graph_id,
                        )
                        .values("data", "resourceinstance_id")
                        .iterator(chunk_size=2000)
                    )

                    for tile in tile_queryset:
                        tiledata = tile.get("data") or {}
                        tile_resource_id = str(tile.get("resourceinstance_id"))

                        for node_id in node_id_set:
                            if node_id not in tiledata:
                                continue

                            node_value = NodeValue(raw=tiledata.get(node_id))
                            referenced_ids = node_value.extract_resource_id()

                            if referenced_ids & source_resource_id:
                                target_id.add(tile_resource_id)
                                break

        if target_id:
            verified_target_id = set()
            target_id_list = list(target_id)

            for chunk in chunked_iterable(target_id_list, BATCH_SIZE):
                verified_ids = ResourceInstance.objects.filter(
                    graph_id=target_graph_id,
                    resourceinstanceid__in=chunk,
                ).values_list("resourceinstanceid", flat=True)

                verified_target_id.update(str(rid) for rid in verified_ids)

            return verified_target_id

        return target_id

    def _get_target_resources_connected_to(
        self,
        target_resource_id: set[str],
        target_graph_id: str,
        linked_resource_id: set[str],
        linked_graph_id: str,
    ) -> set[str]:
        """
        Find target resources that are connected to both the current target set
        AND the linked resources. Used for multi-hop relational filtering.
        """

        if not target_resource_id or not linked_resource_id:
            return set()

        if not LinkNodeCache._initialized:
            LinkNodeCache._initialize()

        referencing_resources = self._get_resources_referencing(
            linked_resource_id, linked_graph_id
        )

        target_id_list = list(target_resource_id)
        linked_id_list = list(linked_resource_id)

        def process_referencing_graph(
            referencing_graph_id: str,
            referencing_resource_id: set[str],
        ) -> set[str]:
            close_old_connections()

            result = set()

            link_nodes = LinkNodeCache.get_link_nodes(
                referencing_graph_id, target_graph_id
            )

            if not link_nodes:
                return result

            node_id_set = {info["node_id"] for info in link_nodes}

            if len(referencing_resource_id) > len(target_resource_id) * 10:
                target_refs_forward = set(
                    ResourceXResource.objects.filter(
                        to_resource_id__in=target_id_list,
                        from_resource_id__in=list(referencing_resource_id),
                    ).values_list("to_resource_id", flat=True)
                )

                result.update(str(rid) for rid in target_refs_forward)

                target_refs_reverse = set(
                    ResourceXResource.objects.filter(
                        from_resource_id__in=target_id_list,
                        to_resource_id__in=list(referencing_resource_id),
                    ).values_list("from_resource_id", flat=True)
                )

                result.update(str(rid) for rid in target_refs_reverse)
            else:
                nodegroup_id = [info["nodegroup_id"] for info in link_nodes]
                referencing_id_list = list(referencing_resource_id)

                for chunk in chunked_iterable(referencing_id_list, BATCH_SIZE):
                    tile_queryset = (
                        TileModel.objects.filter(
                            resourceinstance_id__in=chunk,
                            nodegroup_id__in=nodegroup_id,
                        )
                        .values("data")
                        .iterator(chunk_size=2000)
                    )

                    for tile in tile_queryset:
                        tiledata = tile.get("data") or {}

                        for node_id in node_id_set:
                            if node_id not in tiledata:
                                continue

                            node_value = NodeValue(raw=tiledata.get(node_id))
                            referenced_target_id = node_value.extract_resource_id()

                            for ref_id in referenced_target_id:
                                if ref_id in target_resource_id:
                                    result.add(ref_id)

            return result

        def process_rxr_forward() -> set[str]:
            close_old_connections()

            forward = ResourceXResource.objects.filter(
                from_resource_id__in=target_id_list,
                to_resource_id__in=linked_id_list,
            ).values_list("from_resource_id", flat=True)

            return {str(rid) for rid in forward}

        def process_rxr_reverse() -> set[str]:
            close_old_connections()

            reverse = ResourceXResource.objects.filter(
                to_resource_id__in=target_id_list,
                from_resource_id__in=linked_id_list,
            ).values_list("to_resource_id", flat=True)

            return {str(rid) for rid in reverse}

        connected_target_id = set()

        with ThreadPoolExecutor(
            max_workers=min(MAX_WORKERS, len(referencing_resources) + 2)
        ) as executor:
            futures = []

            for ref_graph_id, ref_resource_id in referencing_resources.items():
                futures.append(
                    executor.submit(
                        process_referencing_graph, ref_graph_id, ref_resource_id
                    )
                )

            futures.append(executor.submit(process_rxr_forward))
            futures.append(executor.submit(process_rxr_reverse))

            for future in as_completed(futures):
                connected_target_id.update(future.result())

        return connected_target_id

    def _handle_intersection_mode_pagination(
        self,
        search_query_object: dict[str, Any],
        response_object: dict[str, Any],
        section_data_list: list[dict[str, Any]],
        translate_mode: str,
        strict_mode: bool,
    ) -> None:
        """Handle pagination for intersection mode."""

        target_graph_id = self._get_graph_id(translate_mode)

        if not target_graph_id:
            return

        if not LinkNodeCache._initialized:
            LinkNodeCache._initialize()

        cache_key = self._get_cache_key(self._query_data)
        cached_id = cache.get(cache_key)

        if cached_id is not None:
            combined_target_id = set(cached_id)
        else:
            section_data_list = self._detect_section_linkage(section_data_list)

            has_linked_section = any(
                SectionFilter.from_dict(s).linked_section_index is not None
                for s in section_data_list
            )

            if has_linked_section:
                combined_target_id = (
                    self._compute_combined_target_id_with_relational_filter(
                        section_data_list,
                        target_graph_id,
                        strict_mode,
                    )
                )
            else:
                combined_target_id = self._compute_combined_target_id(
                    section_data_list,
                    target_graph_id,
                    strict_mode,
                )

            cache.set(cache_key, list(combined_target_id), CACHE_TIMEOUT)

        total_result = len(combined_target_id)

        if total_result == 0:
            self._update_response(response_object, [], 0, 1)
            response_object["_cross_model_pagination_handled"] = True
            return

        page, per_page, start = self._get_pagination_param(total_result)
        target_id_list = sorted(combined_target_id)

        # Ensure start doesn't exceed the list bounds
        if start >= total_result:
            max_page = max(1, (total_result + per_page - 1) // per_page)
            page = max_page
            start = per_page * (page - 1)

        paginated_id = target_id_list[start : start + per_page]

        if not paginated_id and total_result > 0:
            page = 1
            start = 0
            paginated_id = target_id_list[0:per_page]

        se = SearchEngineFactory().create()
        scroller = ElasticsearchScroller(se=se)

        target_query = Bool()
        target_query.filter(Terms(field="resourceinstanceid", terms=paginated_id))

        target_hit = scroller.scroll_with_source(target_query.dsl)

        self._normalize_hit_display_field(target_hit)
        self._add_permission_property(target_hit)
        self._update_response(response_object, target_hit, total_result, page)

        target_filter = Bool()

        target_filter.filter(
            Terms(field="resourceinstanceid", terms=list(combined_target_id))
        )

        search_query_object["query"].dsl = {"query": target_filter.dsl}

        response_object["_cross_model_pagination_handled"] = True

    def _handle_raw_mode_pagination(
        self,
        search_query_object: dict[str, Any],
        response_object: dict[str, Any],
        section_data_list: list[dict[str, Any]],
    ) -> None:
        """Handle pagination for raw results mode."""

        datatype_factory = DataTypeFactory()
        se = SearchEngineFactory().create()
        scroller = ElasticsearchScroller(se=se)

        cross_model_query = Bool()

        for section_data in section_data_list:
            section = SectionFilter.from_dict(section_data)

            if not section.graph_id:
                continue

            section_query = section.build_query(
                datatype_factory, self._node_cache, self.request
            )

            if not bool_has_clause(section_query):
                continue

            graph_with_filter = Bool()
            graph_with_filter.filter(Terms(field="graph_id", terms=[section.graph_id]))
            graph_with_filter.must(section_query)

            cross_model_query.should(graph_with_filter)

        if not cross_model_query.dsl["bool"]["should"]:
            return

        cross_model_query.dsl["bool"]["minimum_should_match"] = 1

        all_resource_id = scroller.scroll_id_only(cross_model_query.dsl)
        total_result = len(all_resource_id)

        if total_result == 0:
            self._update_response(response_object, [], 0, 1)
            response_object["_cross_model_pagination_handled"] = True
            return

        page, per_page, start = self._get_pagination_param(total_result)
        resource_id_list = sorted(all_resource_id)

        # Ensure start doesn't exceed the list bounds
        if start >= total_result:
            max_page = max(1, (total_result + per_page - 1) // per_page)
            page = max_page
            start = per_page * (page - 1)

        paginated_id = resource_id_list[start : start + per_page]

        if not paginated_id and total_result > 0:
            page = 1
            start = 0
            paginated_id = resource_id_list[0:per_page]

        target_query = Bool()
        target_query.filter(Terms(field="resourceinstanceid", terms=paginated_id))

        target_hit = scroller.scroll_with_source(target_query.dsl)

        self._normalize_hit_display_field(target_hit)
        self._add_permission_property(target_hit)
        self._update_response(response_object, target_hit, total_result, page)

        export_filter = Bool()
        export_filter.must(cross_model_query)
        search_query_object["query"].dsl = {"query": export_filter.dsl}

        response_object["_cross_model_pagination_handled"] = True

    def _normalize_hit_display_field(self, hit_list: list[dict[str, Any]]) -> None:
        """
        Convert display fields from array format to simple strings.
        ES stores these as arrays with language/value objects.
        """

        for hit in hit_list:
            source = hit.get("_source", {})

            for field_name in ("displaydescription", "displayname"):
                field_value = source.get(field_name)

                if isinstance(field_value, list) and field_value:
                    source[field_name] = field_value[0].get("value", "")

    def _parse_query_data(self, querystring_param: Any) -> dict[str, Any]:
        if not querystring_param:
            return {}

        if isinstance(querystring_param, str):
            return JSONDeserializer().deserialize(querystring_param)

        return querystring_param

    def _tile_matches_node_filter(
        self, tiledata: dict[str, Any], node_filter: dict[str, Any]
    ) -> bool:
        """Check if any node filter matches the tile data (OR logic across nodes)."""

        if not node_filter:
            return True

        for node_id, filter_value in node_filter.items():
            tile_value = tiledata.get(node_id)
            matcher = FilterMatcher.from_filter_value(filter_value)

            if matcher.matches(tile_value):
                return True

        return False

    def _update_response(
        self,
        response_object: dict[str, Any],
        hit_list: list[dict[str, Any]],
        total: int,
        page: int,
    ) -> None:
        """Update the response object with translated results and pagination info."""

        response_object["results"]["hits"]["hits"] = hit_list
        response_object["results"]["hits"]["total"] = {"relation": "eq", "value": total}
        response_object["total_results"] = total

        if "paging-filter" not in response_object:
            response_object["paging-filter"] = {}

        pagination_result = self._get_pagination_result(response_object, total, page)
        response_object["paging-filter"]["paginator"] = pagination_result.to_dict()

    def append_dsl(self, search_query_object: dict[str, Any], **kwargs: Any) -> None:
        """
        Build and append ES query for raw mode (translate_mode="none").
        In raw mode, returns resources from any matching model combined with OR.
        """

        querystring_param = kwargs.get("querystring", "{}")
        raw_data = self._parse_query_data(querystring_param)

        self._query_data = raw_data

        if not raw_data:
            return

        section_data_list = raw_data.get("sections", [])
        translate_mode = raw_data.get("translate_mode", TranslateMode.NONE)

        if not section_data_list:
            return

        # For both intersection mode and raw mode, we handle pagination ourselves
        # to avoid ES 10k limit. Reset pagination here; post_search_hook will handle it.
        search_query_object["query"].start = 0
        search_query_object["query"].limit = 1

        # Intersection mode is handled entirely in post_search_hook
        if translate_mode != TranslateMode.NONE:
            return

        self._build_node_cache(section_data_list)

        datatype_factory = DataTypeFactory()
        cross_model_query = Bool()

        for section_data in section_data_list:
            section = SectionFilter.from_dict(section_data)

            if not section.graph_id:
                continue

            section_query = section.build_query(
                datatype_factory, self._node_cache, self.request
            )

            if not bool_has_clause(section_query):
                continue

            # Each section is a separate OR branch (i.e., match resources from any model)
            graph_with_filter = Bool()
            graph_with_filter.filter(Terms(field="graph_id", terms=[section.graph_id]))
            graph_with_filter.must(section_query)

            cross_model_query.should(graph_with_filter)

        if cross_model_query.dsl["bool"]["should"]:
            cross_model_query.dsl["bool"]["minimum_should_match"] = 1

        if bool_has_clause(cross_model_query):
            search_query_object["query"].add_query(cross_model_query)

    def post_search_hook(
        self,
        search_query_object: dict[str, Any],
        response_object: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """
        Handle pagination for both intersection mode and raw mode to avoid ES 10k limit.
        """

        raw_data = self._query_data

        if not raw_data:
            return

        section_data_list = raw_data.get("sections", [])
        strict_mode = raw_data.get("strict_mode", False)
        translate_mode = raw_data.get("translate_mode", TranslateMode.NONE)

        if not section_data_list:
            return

        self._build_node_cache(section_data_list)

        if translate_mode == TranslateMode.NONE:
            self._handle_raw_mode_pagination(
                search_query_object,
                response_object,
                section_data_list,
            )
        else:
            self._handle_intersection_mode_pagination(
                search_query_object,
                response_object,
                section_data_list,
                translate_mode,
                strict_mode,
            )

    def view_data(self) -> dict[str, Any]:
        """Return data needed by the frontend search component."""

        resource_graph = (
            GraphModel.objects.exclude(pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
            .exclude(isresource=False)
            .exclude(is_active=False)
            .exclude(source_identifier__isnull=False)
        )

        searchable_datatype = [
            d.pk for d in DDataType.objects.filter(issearchable=True)
        ]

        searchable_node = Node.objects.filter(
            datatype__in=searchable_datatype,
            graph__is_active=True,
            graph__isresource=True,
            issearchable=True,
        )

        resource_card = CardModel.objects.filter(
            graph__is_active=True,
            graph__isresource=True,
        ).select_related("nodegroup")

        # Only include cards the user has permission to read
        searchable_card = [
            card
            for card in resource_card
            if self.request.user.has_perm("read_nodegroup", card.nodegroup)
        ]

        # Sort graphs alphabetically by name
        sorted_graphs = sorted(
            resource_graph,
            key=lambda g: (
                g.name.get("en", "") if isinstance(g.name, dict) else (g.name or "")
            ).lower(),
        )

        return {
            "cardwidgets": CardXNodeXWidget.objects.filter(node__in=searchable_node),
            "cards": searchable_card,
            "datatypes": DDataType.objects.all(),
            "graphs": sorted_graphs,
            "intersection_targets": self._get_intersection_target(),
            "nodes": searchable_node,
        }
