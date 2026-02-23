"""
Cross-Model Advanced Search

Enables search queries that span multiple Arches resource models and returns
results translated to a single target model via relationship traversal.

Overall Strategy

1. Filter construction - The UI sends a JSON payload containing one or more
   sections (one per resource model). Each section holds groups of card
   filters that map directly to Arches nodegroups and their searchable nodes.
   The dataclass hierarchy SectionFilter > GroupFilter > CardFilter mirrors
   this structure and knows how to compile itself into Elasticsearch Bool
   queries.

2. Elasticsearch execution - Each section's query is run against the
   resources index to produce a set of matching resource-instance IDs per
   graph. Queries for different graphs execute in parallel via a thread pool.

3. Relationship traversal (translation) - When a translate mode is active
   (i.e. a target graph is selected), the Intersector hands each per-graph
   result set to the Translator which walks resource-to-resource links to
   find equivalent IDs in the target graph. Links are discovered through
   two mechanisms:

   - ResourceXResource table.
   - Tile-based resource-instance / resource-instance-list node values.

   Multi-hop traversal through intermediate graphs is supported when no
   direct link exists between a source and target graph.

4. Set operations - The translated ID sets from every section are combined
   with either intersect (default) or union logic to produce the final
   result set. A special correlated filtering step ensures that when a
   linking tile also carries contextual filters, both constraints are
   evaluated against the same tile row.

5. Result injection - The final set of target-graph resource IDs is injected
   back into the Elasticsearch query as a terms filter so the standard Arches
   search pipeline handles pagination, sorting, and display.
"""

from __future__ import annotations

import hashlib
import uuid

from collections import defaultdict
from concurrent.futures import as_completed, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import StrEnum
from typing_extensions import Any

from django.core.cache import cache
from django.db import close_old_connections
from django.db.models import Q

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models.models import (
    CardModel,
    CardXNodeXWidget,
    DDataType,
    GraphModel,
    Node,
    NodeGroup,
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

# Number of resource IDs to process in a single database query to avoid memory issues
BATCH_SIZE = 5000

# Cache timeout in seconds for search results and relationship graphs
CACHE_TIMEOUT = 300

# Number of tiles to process per database iteration
CHUNK_SIZE = 5000

# Elasticsearch has a hard limit of 10,000 results per request without scrolling
ES_LIMIT = 10000

# Maximum number of worker threads for parallel processing
MAX_WORKERS = 8

# How long Elasticsearch keeps the search context alive between scroll requests
SCROLL_TIMEOUT = "2m"


class Logic(StrEnum):
    AND = "and"
    OR = "or"


class MatchType(StrEnum):
    ALL = "all"
    ANY = "any"


class TranslateMode(StrEnum):
    NONE = "none"


def chunk(items: list, size: int):
    """Yield successive chunks of the given size from items."""

    for idx in range(0, len(items), size):
        yield items[idx : idx + size]


def has_clause(query: Bool) -> bool:
    """
    Check if a Bool query has any clauses (must, should, or must_not).

    An empty Bool query is structurally valid in Elasticsearch but will match
    all documents. Callers use this guard to avoid appending no-op queries that
    would widen results unexpectedly.
    """

    dsl = query.dsl["bool"]
    return bool(dsl.get("must") or dsl.get("should") or dsl.get("must_not"))


@dataclass
class NodeValue:
    """
    Wraps a raw tile data value from a resource-instance or resource-instance-list
    node and extracts the referenced resource instance IDs from it.

    Tile data for these node types is stored as a list of dicts with a
    "resourceId" key. This class normalises both the single-value and list
    forms so callers do not need to handle either shape directly.
    """

    raw: Any

    def extract(self) -> set[str]:
        """
        Extract referenced resource instance IDs from resource-instance or
        resource-instance-list datatype values.
        """

        result = set()
        items = (
            self.raw if isinstance(self.raw, list) else [self.raw] if self.raw else []
        )

        for item in items:
            if isinstance(item, dict) and "resourceId" in item:
                result.add(item["resourceId"])

        return result


@dataclass
class CardFilter:
    """
    Represents filter criteria for a single card (nodegroup) in the search.

    Each node in the card contributes one clause to the resulting Bool query.
    Resource-instance nodes are handled separately because their tile data
    structure (a list of dicts with a "resourceId" key) requires custom query
    construction that bypasses the standard datatype append_search_filters path.
    """

    filters: dict[str, Any] = field(default_factory=dict)
    nodegroup: str | None = None

    def _build_resource_instance_query(
        self, node_id: str, filter_value: Any
    ) -> Bool | None:
        """Build an ES query for resource-instance or resource-instance-list nodes."""

        val = filter_value.get("val")

        if not val:
            return None

        items = val if isinstance(val, list) else [val]
        resource_ids = []

        for item in items:
            if isinstance(item, dict) and "resourceId" in item:
                resource_ids.append(item["resourceId"])

            if isinstance(item, str):
                resource_ids.append(item)

        if not resource_ids:
            return None

        query = Bool()

        for rid in resource_ids:
            query.should({"term": {f"tiles.data.{node_id}.resourceId.keyword": rid}})

        if resource_ids:
            query.dsl["bool"]["minimum_should_match"] = 1

        return query

    def _is_valid(self, value: Any) -> bool:
        """Check if a filter value is valid (non-empty, allowing 0 and False)."""

        if not value:
            return False

        if isinstance(value, dict):
            val = value.get("val", "")
            return bool(val) or val == 0 or val is False

        return True

    def build(
        self, factory: DataTypeFactory, nodes: dict[str, Node], request: Any
    ) -> Bool:
        """
        Build an Elasticsearch Bool query from the card's node filters.
        Delegates to each node's datatype to construct the appropriate query syntax.
        """

        query = Bool()

        for node_id, filter_value in self.filters.items():
            if not self._is_valid(filter_value):
                continue

            node = nodes.get(node_id)

            if not node:
                continue

            # Resource-instance nodes need special handling for ES queries
            if node.datatype in ("resource-instance", "resource-instance-list"):
                resource_query = self._build_resource_instance_query(
                    node_id, filter_value
                )

                if resource_query and has_clause(resource_query):
                    query.must(resource_query)

                continue

            # Each datatype knows how to construct its own ES query filters
            datatype = factory.get_instance(node.datatype)

            if hasattr(datatype, "append_search_filters"):
                datatype.append_search_filters(filter_value, node, query, request)

        return query

    @classmethod
    def create(cls, data: dict[str, Any]) -> "CardFilter":
        return cls(
            filters=data.get("filters", {}),
            nodegroup=data.get("nodegroup_id"),
        )


@dataclass
class GroupFilter:
    """
    Represents a group of card filters that can be combined with AND (match all)
    or OR (match any) logic.

    Each card query is wrapped in a Nested clause because tiles are stored as
    nested documents in Elasticsearch. The group's match_type controls whether
    all nested clauses must match (must) or at least one must match (should).
    """

    cards: list[CardFilter] = field(default_factory=list)
    match_type: MatchType = MatchType.ALL
    operator: Logic = Logic.AND

    def build(
        self, factory: DataTypeFactory, nodes: dict[str, Node], request: Any
    ) -> Bool:
        """Build an ES Bool query combining all card filters with the group's match logic."""

        query = Bool()

        for card in self.cards:
            card_query = card.build(factory, nodes, request)

            if not has_clause(card_query):
                continue

            if card_query.dsl["bool"].get("filter"):
                clause = card_query
            else:
                # Wrap tile queries in Nested because tiles are stored as nested documents
                clause = Nested(path="tiles", query=card_query)

            if self.match_type == MatchType.ANY:
                query.should(clause)
            else:
                query.must(clause)

        if query.dsl["bool"]["should"]:
            query.dsl["bool"]["minimum_should_match"] = 1

        return query

    @classmethod
    def create(cls, data: dict[str, Any]) -> "GroupFilter":
        match_val = data.get("match", MatchType.ALL)
        op_val = data.get("operator_after", Logic.AND)

        return cls(
            cards=[CardFilter.create(card) for card in data.get("cards", [])],
            match_type=MatchType(match_val) if match_val else MatchType.ALL,
            operator=Logic(op_val) if op_val else Logic.AND,
        )


@dataclass
class SectionFilter:
    """
    Represents all filter criteria for a single resource model.

    Contains multiple groups that are combined using the operator declared on
    each group. When all inter-group operators are the same (all AND or all OR)
    the query is built directly. Mixed operators are resolved by collecting
    consecutive AND groups into sub-queries that are then OR'd together,
    matching standard boolean precedence.
    """

    graph: str | None = None
    groups: list[GroupFilter] = field(default_factory=list)

    def build(
        self, factory: DataTypeFactory, nodes: dict[str, Node], request: Any
    ) -> Bool:
        """Build an ES Bool query combining all groups with their inter-group operators."""

        query = Bool()
        valid = []

        for group in self.groups:
            group_query = group.build(factory, nodes, request)

            if has_clause(group_query):
                valid.append((group, group_query))

        if not valid:
            return query

        if len(valid) == 1:
            query.must(valid[0][1])
            return query

        ops = [grp.operator for grp, _ in valid[:-1]]
        all_and = all(op == Logic.AND for op in ops)
        all_or = all(op == Logic.OR for op in ops)

        if all_and:
            for _, group_query in valid:
                query.must(group_query)

            return query

        if all_or:
            for _, group_query in valid:
                query.should(group_query)

            query.dsl["bool"]["minimum_should_match"] = 1

            return query

        # Mixed operators: group consecutive ANDs together, then OR the AND-groups
        current_and = []
        or_groups = []

        for idx, (group, group_query) in enumerate(valid):
            current_and.append(group_query)

            if idx < len(valid) - 1 and ops[idx] == Logic.OR:
                or_groups.append(current_and)
                current_and = []

        if current_and:
            or_groups.append(current_and)

        for and_group in or_groups:
            if len(and_group) == 1:
                query.should(and_group[0])
            else:
                and_query = Bool()

                for grp_query in and_group:
                    and_query.must(grp_query)

                query.should(and_query)

        query.dsl["bool"]["minimum_should_match"] = 1

        return query

    @classmethod
    def create(cls, data: dict[str, Any]) -> "SectionFilter":
        return cls(
            graph=data.get("graph_id"),
            groups=[GroupFilter.create(grp) for grp in data.get("groups", [])],
        )


class LinkCache:
    """
    Singleton cache for resource-instance node configurations across all graphs.

    Tracks which graphs can link to which other graphs via resource-instance or
    resource-instance-list nodes. This information drives relationship traversal
    during cross-model searches without requiring repeated database queries.

    Nodes are divided into two categories:

    - Constrained nodes: their config declares one or more explicit target graph
      IDs, so they can only reference resources in those specific graphs.
    - Unconstrained nodes: their config contains no graphid restriction, meaning
      they can reference resources in any graph.

    Both categories are returned by get(), but only constrained nodes are
    returned by get_constrained(). Correlated filtering relies exclusively on
    constrained nodes because unconstrained nodes cannot guarantee the link
    points at the intended target graph.
    """

    _cache: dict[tuple[str, str], list[dict[str, Any]]] = {}
    _child_nodegroups: set[str] = set()
    _constrained_cache: dict[tuple[str, str], list[dict[str, Any]]] = {}
    _graph_nodes: dict[str, list[dict[str, Any]]] = {}
    _ready: bool = False
    _unconstrained: dict[str, list[dict[str, Any]]] = {}

    @classmethod
    def _extract_target(cls, config: dict[str, Any]) -> list[str]:
        """
        Extract target graph IDs from a resource-instance node's config.
        Handles both legacy format (graphid) and new format (graphs array).
        """

        result = []

        if "graphid" in config:
            val = config.get("graphid")

            if val:
                if isinstance(val, list):
                    result.extend(val)
                else:
                    result.append(val)

        if "graphs" in config:
            for graph in config.get("graphs", []):
                if isinstance(graph, dict) and graph.get("graphid"):
                    result.append(graph["graphid"])

        return [str(gid) for gid in result]

    @classmethod
    def _init(cls) -> None:
        """
        Load all resource-instance nodes from the database and categorize them
        as constrained or unconstrained.

        Constrained nodes are indexed under _graph_nodes by their source graph ID.
        Unconstrained nodes are stored separately under _unconstrained so that
        get() can include them while get_constrained() can exclude them.

        Child nodegroups are also collected here so that correlated filtering
        can identify nested tiles that carry both a relationship link and
        contextual filter values on the same tile row.
        """

        nodes = Node.objects.filter(
            datatype__in=["resource-instance", "resource-instance-list"],
        ).values("config", "graph_id", "nodegroup_id", "nodeid")

        for node in nodes:
            graph_id = str(node["graph_id"])
            targets = cls._extract_target(node["config"] or {})

            info = {
                "node": str(node["nodeid"]),
                "nodegroup": str(node["nodegroup_id"]),
                "targets": set(targets),
            }

            if graph_id not in cls._graph_nodes:
                cls._graph_nodes[graph_id] = []

            if targets:
                cls._graph_nodes[graph_id].append(info)
            else:
                # Nodes without target constraints can reference any graph
                if graph_id not in cls._unconstrained:
                    cls._unconstrained[graph_id] = []

                cls._unconstrained[graph_id].append(info)

        # Track child nodegroups for correlated filtering
        cls._child_nodegroups = set(
            str(ng.nodegroupid)
            for ng in NodeGroup.objects.filter(parentnodegroup__isnull=False).only(
                "nodegroupid"
            )
        )

        cls._ready = True

    @classmethod
    def clear(cls) -> None:
        """Clear all cached data."""

        cls._cache.clear()
        cls._child_nodegroups.clear()
        cls._constrained_cache.clear()
        cls._graph_nodes.clear()
        cls._ready = False
        cls._unconstrained.clear()

    @classmethod
    def get(cls, source: str, target: str) -> list[dict[str, Any]]:
        """
        Get all nodes in source_graph that can reference resources in target_graph.
        Returns both explicitly constrained nodes and unconstrained nodes.
        """

        if not cls._ready:
            cls._init()

        key = (source, target)

        if key in cls._cache:
            return cls._cache[key]

        result = []

        for info in cls._graph_nodes.get(source, []):
            if target in info["targets"]:
                result.append({"node": info["node"], "nodegroup": info["nodegroup"]})

        # Unconstrained nodes can link to any graph
        for info in cls._unconstrained.get(source, []):
            result.append({"node": info["node"], "nodegroup": info["nodegroup"]})

        cls._cache[key] = result
        return result

    @classmethod
    def get_constrained(cls, source: str, target: str) -> list[dict[str, Any]]:
        """
        Get only explicitly constrained nodes (excludes unconstrained nodes).

        Used by correlated filtering, which requires certainty that a node's
        tile value points at the intended target graph before evaluating
        additional filter conditions on the same tile row.
        """

        if not cls._ready:
            cls._init()

        key = (source, target)

        if key in cls._constrained_cache:
            return cls._constrained_cache[key]

        result = []

        for info in cls._graph_nodes.get(source, []):
            if target in info["targets"]:
                result.append({"node": info["node"], "nodegroup": info["nodegroup"]})

        cls._constrained_cache[key] = result
        return result

    @classmethod
    def is_child_nodegroup(cls, nodegroup_id: str) -> bool:
        """Check if a nodegroup is a child (nested) nodegroup."""

        if not cls._ready:
            cls._init()

        return nodegroup_id in cls._child_nodegroups


class Scroller:
    """
    Handles scrolling through large Elasticsearch result sets that exceed the
    10,000-hit default limit.

    For ID-only queries, composite aggregations are preferred over the scroll
    API because they are more memory-efficient on the Elasticsearch side and
    do not require keeping a scroll context open between requests.
    """

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    def _clear(self, scroll_id: str | None) -> None:
        """Release the scroll context to free resources."""

        if not scroll_id:
            return

        try:
            self.engine.es.clear_scroll(scroll_id=scroll_id)
        except Exception:
            pass

    def hits(
        self, query: dict[str, Any], source: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Scroll through results returning full documents or specified fields."""

        result = []

        response = self.engine.search(
            _source=source if source else True,
            index=RESOURCES_INDEX,
            query=query,
            scroll=SCROLL_TIMEOUT,
            size=ES_LIMIT,
        )

        scroll_id = response.get("_scroll_id")
        result.extend(response.get("hits", {}).get("hits", []))

        while response.get("hits", {}).get("hits", []):
            response = self.engine.es.scroll(scroll_id=scroll_id, scroll=SCROLL_TIMEOUT)
            scroll_id = response.get("_scroll_id")
            result.extend(response.get("hits", {}).get("hits", []))

        self._clear(scroll_id)

        return result

    def ids(self, query: dict[str, Any]) -> set[str]:
        """
        Return only the resource instance IDs matching the query.

        For result sets up to 10,000 hits a simple size-limited query is used.
        Beyond that, composite aggregations page through the full result set
        without holding a scroll context open, which is more efficient than
        the scroll API for large cardinality ID retrieval.
        """

        result = set()

        # First get the count to determine strategy
        count_response = self.engine.search(
            index=RESOURCES_INDEX,
            query=query,
            size=0,
            track_total_hits=True,
        )
        total = count_response.get("hits", {}).get("total", {}).get("value", 0)

        if total == 0:
            return result

        # For small result sets, use a simple query
        if total <= 10000:
            response = self.engine.search(
                index=RESOURCES_INDEX,
                query=query,
                size=total,
                _source=False,
            )

            for hit in response.get("hits", {}).get("hits", []):
                result.add(hit["_id"])

            return result

        # For large result sets, use composite aggregations (more efficient than scroll)
        after_key = None

        while True:
            aggs = {
                "ids": {
                    "composite": {
                        "size": 10000,
                        "sources": [
                            {"rid": {"terms": {"field": "resourceinstanceid"}}}
                        ],
                    }
                }
            }

            if after_key:
                aggs["ids"]["composite"]["after"] = after_key

            response = self.engine.search(
                index=RESOURCES_INDEX,
                query=query,
                size=0,
                aggs=aggs,
            )

            buckets = response.get("aggregations", {}).get("ids", {}).get("buckets", [])

            if not buckets:
                break

            for bucket in buckets:
                result.add(bucket["key"]["rid"])

            after_key = response.get("aggregations", {}).get("ids", {}).get("after_key")

            if not after_key:
                break

        return result


class Linker:
    """
    Resolves connections between resources across different graphs.

    Uses two discovery mechanisms in order of preference:

    1. ResourceXResource table — explicit, graph-aware relationships that are
       fast to query and carry no ambiguity about which graph the linked
       resource belongs to.
    2. Tile data — resource-instance node values stored inside tile JSON. Used
       as a fallback when no ResourceXResource rows exist for the given pair of
       graphs, and also for correlated filtering where the link and any
       additional filters must be evaluated against the same tile row.
    """

    def _find_forward_via_tiles(
        self,
        sources: list[str],
        source_graph: str,
        target_graph: str,
    ) -> set[str]:
        """Find target resources by scanning tiles for resource-instance references."""

        forward_links = LinkCache.get(source_graph, target_graph)

        if not forward_links:
            return set()

        nodegroups = {info["nodegroup"] for info in forward_links}
        nodes = {info["node"] for info in forward_links}
        result = set()

        for batch in chunk(sources, BATCH_SIZE):
            tiles = (
                TileModel.objects.filter(
                    nodegroup_id__in=nodegroups,
                    resourceinstance_id__in=batch,
                )
                .values("data")
                .iterator(chunk_size=CHUNK_SIZE)
            )

            for tile in tiles:
                data = tile.get("data") or {}

                for node_id in nodes:
                    if node_id not in data:
                        continue

                    result.update(NodeValue(raw=data.get(node_id)).extract())

        return result

    def _find_reverse_via_tiles(
        self,
        sources: list[str],
        nodes: set[str],
        nodegroups: set[str],
        graph: str,
    ) -> set[str]:
        """
        Find resources in the target graph whose tiles reference one of the
        source resources.

        For small source sets (up to 100 IDs), Django Q objects are used to
        push the filtering into the database. For larger sets, all matching
        tiles are streamed and filtered in Python to avoid generating an
        oversized IN clause.
        """

        if not sources or not nodes or not nodegroups:
            return set()

        # For small source sets, use Django Q objects for efficient querying
        if len(sources) <= 100:
            result = set()
            query = Q()

            for source_id in sources:
                for node_id in nodes:
                    query |= Q(
                        **{f"data__{node_id}__contains": [{"resourceId": source_id}]}
                    )

            if query:
                tiles = (
                    TileModel.objects.filter(
                        query,
                        nodegroup_id__in=nodegroups,
                        resourceinstance__graph_id=graph,
                    )
                    .values_list("resourceinstance_id", flat=True)
                    .distinct()
                )

                result.update(str(rid) for rid in tiles)

            return result

        # For larger sets, scan all tiles and filter in Python
        source_set = set(sources)
        result = set()

        tiles = (
            TileModel.objects.filter(
                nodegroup_id__in=nodegroups,
                resourceinstance__graph_id=graph,
            )
            .values("data", "resourceinstance_id")
            .iterator(chunk_size=CHUNK_SIZE)
        )

        for tile in tiles:
            data = tile.get("data") or {}
            resource_id = str(tile.get("resourceinstance_id"))

            for node_id in nodes:
                if node_id not in data:
                    continue

                refs = NodeValue(raw=data.get(node_id)).extract()

                if refs & source_set:
                    result.add(resource_id)
                    break

        return result

    def _tile_matches_filters(
        self, data: dict[str, Any], tile_filters: dict[str, Any]
    ) -> bool:
        """Check if tile data matches all specified filter criteria."""

        for node_id, filter_value in tile_filters.items():
            if node_id not in data:
                return False

            tile_value = data.get(node_id)
            op = filter_value.get("op", "eq")
            val = filter_value.get("val")

            if not self._value_matches(tile_value, val, op):
                return False

        return True

    def _value_matches(self, tile_value: Any, filter_val: Any, op: str) -> bool:
        """Check if a tile value matches a filter value with the given operator."""

        if tile_value is None:
            return False

        # Handle concept/controlled list comparisons via URI
        if isinstance(filter_val, list):
            filter_uris = set()

            for item in filter_val:
                if isinstance(item, dict) and "uri" in item:
                    filter_uris.add(item["uri"])

            tile_uris = set()

            if isinstance(tile_value, list):
                for item in tile_value:
                    if isinstance(item, dict) and "uri" in item:
                        tile_uris.add(item["uri"])
            elif isinstance(tile_value, dict) and "uri" in tile_value:
                tile_uris.add(tile_value["uri"])

            if op == "eq":
                return bool(filter_uris & tile_uris)

            if op in ("neq", "!eq"):
                return not bool(filter_uris & tile_uris)

        # Simple value comparisons
        if op == "eq":
            return tile_value == filter_val

        if op in ("neq", "!eq"):
            return tile_value != filter_val

        if op == "gt":
            return tile_value > filter_val

        if op == "gte":
            return tile_value >= filter_val

        if op == "lt":
            return tile_value < filter_val

        if op == "lte":
            return tile_value <= filter_val

        return False

    def get_connected(self, sources: set[str]) -> set[str]:
        """Get all resources connected to source resources via ResourceXResource."""

        if not sources:
            return set()

        result = set()
        source_list = list(sources)

        for batch in chunk(source_list, BATCH_SIZE):
            forward = ResourceXResource.objects.filter(
                from_resource_id__in=batch,
            ).values_list("to_resource_id", flat=True)

            result.update(str(rid) for rid in forward)

            reverse = ResourceXResource.objects.filter(
                to_resource_id__in=batch,
            ).values_list("from_resource_id", flat=True)

            result.update(str(rid) for rid in reverse)

        return result

    def get_intermediate(
        self, sources: set[str], source_graph: str, target_graph: str
    ) -> set[str]:
        """
        Find target graph resources connected to the source resources.

        Queries ResourceXResource in both forward and reverse directions first.
        Falls back to tile-based link discovery only if no RXR rows are found,
        checking both forward (source tiles reference target) and reverse
        (target tiles reference source) tile directions.

        Results are verified against the database to confirm they belong to the
        expected target graph, guarding against stale or cross-graph ID collisions.
        """

        if not sources:
            return set()

        if source_graph == target_graph:
            return sources

        result = set()
        source_list = list(sources)

        # Try ResourceXResource first (forward direction)
        for batch in chunk(source_list, BATCH_SIZE):
            rxr = ResourceXResource.objects.filter(
                from_resource_id__in=batch,
                to_resource_graph_id=target_graph,
            ).values_list("to_resource_id", flat=True)

            result.update(str(rid) for rid in rxr)

        # Try ResourceXResource (reverse direction)
        for batch in chunk(source_list, BATCH_SIZE):
            rxr = ResourceXResource.objects.filter(
                to_resource_id__in=batch,
                from_resource_graph_id=target_graph,
            ).values_list("from_resource_id", flat=True)

            result.update(str(rid) for rid in rxr)

        # Fall back to tile-based links if RXR didn't find anything
        if not result:
            forward_links = LinkCache.get(source_graph, target_graph)

            if forward_links:
                result.update(
                    self._find_forward_via_tiles(
                        source_list, source_graph, target_graph
                    )
                )

            reverse_links = LinkCache.get(target_graph, source_graph)

            if reverse_links:
                nodegroups = {info["nodegroup"] for info in reverse_links}
                nodes = {info["node"] for info in reverse_links}
                result.update(
                    self._find_reverse_via_tiles(
                        source_list, nodes, nodegroups, target_graph
                    )
                )

        # Verify results actually exist in target graph
        if result:
            verified = set()

            for batch in chunk(list(result), BATCH_SIZE):
                ids = ResourceInstance.objects.filter(
                    graph_id=target_graph,
                    resourceinstanceid__in=batch,
                ).values_list("resourceinstanceid", flat=True)

                verified.update(str(rid) for rid in ids)

            return verified

        return result

    def get_linked_from_tiles(
        self,
        source_ids: set[str],
        source_graph: str,
        target_graph: str,
        nodegroup_ids: set[str],
        tile_filters: dict[str, Any] | None = None,
    ) -> dict[str, set[str]]:
        """
        Build a mapping of source resource IDs to the target resource IDs they
        reference via tile data, constrained to the given nodegroups.

        When tile_filters is provided, only tiles whose data satisfies every
        filter condition are included. This is the mechanism behind correlated
        filtering: a tile that carries both a resource-instance link and a
        contextual filter value (e.g. a relationship type) must satisfy both
        constraints on the same row before the link is counted.
        """

        result = defaultdict(set)

        forward_links = LinkCache.get(source_graph, target_graph)

        if not forward_links:
            return result

        link_nodes = {info["node"] for info in forward_links}
        nodegroups = {info["nodegroup"] for info in forward_links} & nodegroup_ids

        if not nodegroups:
            return result

        source_list = list(source_ids)

        for batch in chunk(source_list, BATCH_SIZE):
            tiles = (
                TileModel.objects.filter(
                    nodegroup_id__in=nodegroups,
                    resourceinstance_id__in=batch,
                )
                .values("data", "resourceinstance_id")
                .iterator(chunk_size=CHUNK_SIZE)
            )

            for tile in tiles:
                data = tile.get("data") or {}
                source_id = str(tile.get("resourceinstance_id"))

                # Apply additional tile filters if specified
                if tile_filters and not self._tile_matches_filters(data, tile_filters):
                    continue

                for node_id in link_nodes:
                    if node_id not in data:
                        continue

                    linked = NodeValue(raw=data.get(node_id)).extract()
                    result[source_id].update(linked)

        return result


class Translator:
    """
    Translates a set of source graph resource IDs to equivalent IDs in a target
    graph by following resource relationships.

    Translation is attempted in three stages of increasing breadth:

    1. Direct link — a single get_intermediate call between source and target.
    2. Multi-hop — routes through an intermediate graph that connects both the
       source and the target. ES filter sets for the intermediate graph are
       applied to narrow the hop.
    3. Broad connected set — collects all resources reachable from the sources
       via ResourceXResource and intersects them with available ES match sets
       before attempting a final hop to the target.
    """

    def __init__(self, linker: Linker) -> None:
        self.linker = linker

    def translate(
        self,
        sources: set[str],
        source_graph: str,
        target_graph: str,
        adjacency: dict[str, list[str]],
        es_matches: dict[str, set[str]],
    ) -> set[str]:
        """
        Translate source resources to target graph resources.
        Tries direct links first, then multi-hop traversal through intermediate graphs.
        """

        if source_graph == target_graph:
            return sources

        # Try direct translation first
        result = self.linker.get_intermediate(sources, source_graph, target_graph)

        if result:
            return result

        # Try multi-hop through intermediate graphs
        for intermediate_graph in adjacency.keys():
            if intermediate_graph in (source_graph, target_graph):
                continue

            # Check if we can reach intermediate from source and target from intermediate
            can_reach_intermediate = intermediate_graph in adjacency.get(
                source_graph, []
            ) or source_graph in adjacency.get(intermediate_graph, [])
            can_reach_target = target_graph in adjacency.get(
                intermediate_graph, []
            ) or intermediate_graph in adjacency.get(target_graph, [])

            if not (can_reach_intermediate and can_reach_target):
                continue

            intermediate_resources = self.linker.get_intermediate(
                sources, source_graph, intermediate_graph
            )

            if not intermediate_resources:
                continue

            # Apply ES filters to intermediate if available
            if intermediate_graph in es_matches:
                intermediate_resources &= es_matches[intermediate_graph]

                if not intermediate_resources:
                    continue

            target_resources = self.linker.get_intermediate(
                intermediate_resources, intermediate_graph, target_graph
            )

            result.update(target_resources)

        if result:
            return result

        # Last resort: find any connected resources and filter by ES matches
        connected = self.linker.get_connected(sources)

        if not connected:
            return result

        for graph_id, matches in es_matches.items():
            if graph_id in (source_graph, target_graph):
                continue

            filtered = connected & matches

            if filtered:
                target_resources = self.linker.get_intermediate(
                    filtered, graph_id, target_graph
                )
                result.update(target_resources)

        return result


class Intersector:
    """
    Top-level coordinator that turns per-section filter data into a final set
    of target graph resource IDs.

    Pipeline:

    1. Parse each section into a SectionFilter and group them by graph.
    2. Execute ES queries for all graphs in parallel, producing a per-graph
       match set.
    3. Optionally apply correlated filtering to pairs of graphs whose linking
       tiles also carry contextual filter values, ensuring both the link and
       the filter are evaluated on the same tile row.
    4. Build a graph adjacency map that includes intermediate graphs capable
       of bridging the filtered graphs to the target.
    5. Translate each per-graph match set to the target graph in parallel,
       then combine the translated sets using the chosen set operation
       (intersect or union).
    """

    def __init__(
        self,
        factory: DataTypeFactory,
        linker: Linker,
        nodes: dict[str, Node],
        request: Any,
        scroller: Scroller,
    ) -> None:
        self._factory = factory
        self._linker = linker
        self._nodes = nodes
        self._request = request
        self._scroller = scroller
        self._translator = Translator(linker)

    def _apply_correlated_filtering(
        self,
        es_matches: dict[str, set[str]],
        section_lookup: dict[str, SectionFilter],
        operation: str,
    ) -> dict[str, set[str]] | None:
        """
        Apply correlated filtering between sections.
        Ensures that linked resources match through the same tile that passes filters.
        """

        correlated_pairs = []

        for source_graph, source_section in section_lookup.items():
            for other_graph in es_matches.keys():
                if source_graph == other_graph:
                    continue

                linking_nodegroups = self._find_correlated_nodegroups(
                    source_graph, other_graph, source_section
                )

                if linking_nodegroups:
                    correlated_pairs.append(
                        (source_graph, other_graph, linking_nodegroups)
                    )

        for source_graph, linked_graph, linking_nodegroups in correlated_pairs:
            source_matches = es_matches[source_graph]
            linked_matches = es_matches[linked_graph]
            source_section = section_lookup.get(source_graph)

            all_linked = set()
            linked_map_combined = defaultdict(set)

            for nodegroup_id in linking_nodegroups:
                nodegroup_filters = self._get_filters_for_nodegroups(
                    source_section, {nodegroup_id}
                )

                linked_map = self._linker.get_linked_from_tiles(
                    source_matches,
                    source_graph,
                    linked_graph,
                    {nodegroup_id},
                    nodegroup_filters if nodegroup_filters else None,
                )

                for source_id, linked_ids in linked_map.items():
                    linked_map_combined[source_id].update(linked_ids)
                    all_linked.update(linked_ids)

            correlated_linked = all_linked & linked_matches

            if not correlated_linked:
                if operation == "intersect":
                    return None

                continue

            # Keep only source resources that link to matching linked resources
            filtered_sources = {
                source_id
                for source_id, linked_ids in linked_map_combined.items()
                if linked_ids & correlated_linked
            }

            es_matches[source_graph] = filtered_sources
            es_matches[linked_graph] = correlated_linked

        return es_matches

    def _build_adjacency(
        self, sections: list[SectionFilter], target_graph: str
    ) -> dict[str, list[str]]:
        """
        Build an adjacency map of graph connections for translation.

        Starts from the set of graphs that carry active filters plus the target
        graph. Candidate intermediate graphs (those not in the filtered set) are
        included when they have connections to two or more filtered graphs, as
        they may provide a bridge for multi-hop translation. Edges are populated
        from both the LinkCache and existing ResourceXResource rows.
        """

        filtered_graphs = {section.graph for section in sections if section.graph}
        filtered_graphs.add(target_graph)

        all_graphs = set(
            str(g.graphid)
            for g in GraphModel.objects.filter(isresource=True, is_active=True)
            .exclude(pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
            .only("graphid")
        )

        # Find intermediate graphs that connect multiple filtered graphs
        intermediate_graphs = set()

        for candidate in all_graphs:
            if candidate in filtered_graphs:
                continue

            connections_to_filtered = 0

            for filtered_graph in filtered_graphs:
                if LinkCache.get(candidate, filtered_graph) or LinkCache.get(
                    filtered_graph, candidate
                ):
                    connections_to_filtered += 1

            for filtered_graph in filtered_graphs:
                has_rxr = (
                    ResourceXResource.objects.filter(
                        from_resource_graph_id=candidate,
                        to_resource_graph_id=filtered_graph,
                    ).exists()
                    or ResourceXResource.objects.filter(
                        from_resource_graph_id=filtered_graph,
                        to_resource_graph_id=candidate,
                    ).exists()
                )

                if has_rxr:
                    connections_to_filtered += 1

            # Include if connects to 2+ filtered graphs
            if connections_to_filtered >= 2:
                intermediate_graphs.add(candidate)

        graphs = filtered_graphs | intermediate_graphs
        adjacency = {graph: [] for graph in graphs}

        # Build adjacency from link cache
        for source in graphs:
            for dest in graphs:
                if source != dest and LinkCache.get(source, dest):
                    adjacency[source].append(dest)

        # Add RXR-based adjacency
        graph_list = list(graphs)

        rxr_links = (
            ResourceXResource.objects.filter(
                from_resource_graph_id__in=graph_list,
                to_resource_graph_id__in=graph_list,
            )
            .values("from_resource_graph_id", "to_resource_graph_id")
            .distinct()
        )

        for link in rxr_links:
            source = str(link["from_resource_graph_id"])
            dest = str(link["to_resource_graph_id"])

            if source in adjacency and dest not in adjacency[source]:
                adjacency[source].append(dest)

        return adjacency

    def _execute_section(self, section: SectionFilter) -> set[str]:
        """Run the ES query for a section and return all matching resource IDs."""

        if not section.graph:
            return set()

        query = section.build(self._factory, self._nodes, self._request)

        if not has_clause(query):
            return set()

        full_query = Bool()
        full_query.filter(Terms(field="graph_id", terms=[section.graph]))
        full_query.must(query)

        return self._scroller.ids(full_query.dsl)

    def _find_correlated_nodegroups(
        self,
        source_graph: str,
        target_graph: str,
        source_section: SectionFilter,
    ) -> set[str]:
        """
        Identify child nodegroups that carry both a constrained link to the
        target graph and at least one non-resource-instance filter value.

        Only child (nested) nodegroups are considered because a correlated
        filter requires the link and the contextual filter to exist on the same
        tile row. Top-level nodegroups cannot share a row with another tile's
        link value, so they are excluded.
        """

        links = LinkCache.get_constrained(source_graph, target_graph)

        if not links:
            return set()

        # Only consider child nodegroups (nested tiles)
        link_nodegroups = {
            info["nodegroup"]
            for info in links
            if LinkCache.is_child_nodegroup(info["nodegroup"])
        }

        if not link_nodegroups:
            return set()

        valid_nodegroups = set()

        for group in source_section.groups:
            for card in group.cards:
                if not card.nodegroup or card.nodegroup not in link_nodegroups:
                    continue

                has_contextual_filter = False

                for node_id, filter_value in card.filters.items():
                    if not filter_value or not filter_value.get("val"):
                        continue

                    node = self._nodes.get(node_id)

                    # Non-resource-instance filters are contextual
                    if not node or node.datatype not in (
                        "resource-instance",
                        "resource-instance-list",
                    ):
                        has_contextual_filter = True
                        break

                if has_contextual_filter:
                    valid_nodegroups.add(card.nodegroup)

        return valid_nodegroups

    def _get_filters_for_nodegroups(
        self,
        section: SectionFilter,
        nodegroups: set[str],
    ) -> dict[str, Any]:
        """Extract all filter values for the specified nodegroups."""

        filters = {}

        for group in section.groups:
            for card in group.cards:
                if card.nodegroup not in nodegroups:
                    continue

                for node_id, filter_value in card.filters.items():
                    if filter_value and filter_value.get("val"):
                        filters[node_id] = filter_value

        return filters

    def _has_correlated_pairs(
        self,
        graphs_with_filters: set[str],
        section_lookup: dict[str, SectionFilter],
    ) -> bool:
        """Check if any pair of graphs requires correlated filtering."""

        for source_graph in graphs_with_filters:
            source_section = section_lookup.get(source_graph)

            if not source_section:
                continue

            for other_graph in graphs_with_filters:
                if source_graph != other_graph:
                    if self._find_correlated_nodegroups(
                        source_graph, other_graph, source_section
                    ):
                        return True

        return False

    def _run_es_queries(
        self, by_graph: dict[str, list[SectionFilter]]
    ) -> dict[str, set[str]]:
        """Run ES queries for all graphs in parallel."""

        es_matches = {}

        with ThreadPoolExecutor(max_workers=min(len(by_graph), MAX_WORKERS)) as pool:
            futures = {}

            for graph, graph_sections in by_graph.items():
                futures[pool.submit(self._run_graph_queries, graph_sections)] = graph

            for future in as_completed(futures):
                graph = futures[future]
                es_matches[graph] = future.result()

        return es_matches

    def _run_graph_queries(self, sections: list[SectionFilter]) -> set[str]:
        """Run ES queries for all sections of a single graph and intersect results."""

        combined = None

        for section in sections:
            matches = self._execute_section(section)

            if not matches:
                return set()

            combined = matches if combined is None else combined & matches

        return combined or set()

    def _translate_graph(
        self,
        source_graph: str,
        matches: set[str],
        target_graph: str,
        adjacency: dict[str, list[str]],
        es_matches: dict[str, set[str]],
    ) -> set[str]:
        """Translate a single graph's matches to the target graph (thread-safe)."""

        close_old_connections()

        return self._translator.translate(
            matches, source_graph, target_graph, adjacency, es_matches
        )

    def _translate_to_target(
        self,
        es_matches: dict[str, set[str]],
        target_graph: str,
        adjacency: dict[str, list[str]],
        operation: str,
    ) -> set[str]:
        """Translate all ES matches to the target graph and combine with operation."""

        if target_graph in es_matches:
            result = es_matches[target_graph]
        else:
            result = None if operation == "intersect" else set()

        graphs_to_translate = [
            (source_graph, matches)
            for source_graph, matches in es_matches.items()
            if source_graph != target_graph
        ]

        if not graphs_to_translate:
            return result or set()

        with ThreadPoolExecutor(
            max_workers=min(len(graphs_to_translate), MAX_WORKERS)
        ) as pool:
            futures = {
                pool.submit(
                    self._translate_graph,
                    source_graph,
                    matches,
                    target_graph,
                    adjacency,
                    es_matches,
                ): source_graph
                for source_graph, matches in graphs_to_translate
            }

            for future in as_completed(futures):
                translated = future.result()

                if operation == "intersect":
                    if not translated:
                        return set()

                    result = translated if result is None else result & translated
                else:
                    result.update(translated)

        return result or set()

    def compute(
        self,
        section_data: list[dict[str, Any]],
        target_graph: str,
        operation: str = "intersect",
    ) -> set[str]:
        """
        Compute the final set of target graph resource IDs from all section filters.

        Steps:
        1. Parse section_data into SectionFilter objects, grouped by graph.
        2. Run ES queries for each graph in parallel.
        3. Return early if any graph yields no matches (intersect only).
        4. Apply correlated filtering if any two graphs share a linking child
           nodegroup that also carries contextual filter values.
        5. Build a graph adjacency map, including intermediate graphs.
        6. Translate each per-graph match set to the target graph in parallel.
        7. Combine translated sets using the specified operation.
        """

        sections = [SectionFilter.create(data) for data in section_data]

        if not sections:
            return set()

        # Group sections by graph
        by_graph = defaultdict(list)
        section_lookup = {}

        for section in sections:
            if section.graph:
                by_graph[section.graph].append(section)
                section_lookup[section.graph] = section

        # Run ES queries for all graphs in parallel
        es_matches = self._run_es_queries(by_graph)

        # Early exit if any graph has no matches (for intersect)
        if operation == "intersect" and any(
            not matches for matches in es_matches.values()
        ):
            return set()

        # Apply correlated filtering if needed
        if len(es_matches) > 1 and self._has_correlated_pairs(
            set(es_matches.keys()), section_lookup
        ):
            es_matches = self._apply_correlated_filtering(
                es_matches, section_lookup, operation
            )

            if es_matches is None or (
                operation == "intersect"
                and any(not matches for matches in es_matches.values())
            ):
                return set()

        # Build graph adjacency for translation
        adjacency = self._build_adjacency(sections, target_graph)

        # Translate all results to target graph
        return self._translate_to_target(es_matches, target_graph, adjacency, operation)


class CrossModelAdvancedSearch(BaseSearchFilter):
    """
    Search filter that enables queries spanning multiple resource models.

    Supports two modes selected via the translate_mode parameter:

    - Raw mode (translate_mode="none"): Returns resources from any of the
      filtered models combined with OR logic. No relationship traversal occurs.
    - Intersection mode (translate_mode=<graph_slug_or_id>): Runs ES queries
      against each filtered model, traverses ResourceXResource relationships
      and tile-based resource-instance links to find connected resources in the
      target model, then combines the per-model result sets using the chosen
      operation (intersect or union) before injecting a terms filter into the
      main ES query.

    Results in intersection mode are cached by a hash of the search parameters
    and the requesting user's ID to avoid redundant traversal on repeated or
    paginated requests.
    """

    _data = None
    _nodes: dict[str, Node] = {}
    _target_ids: set[str] | None = None

    def _build_cache(self, sections: list[dict[str, Any]]) -> None:
        """Preload all nodes referenced in filters to avoid repeated database queries."""

        node_ids = set()

        for section in sections:
            for group in section.get("groups", []):
                for card in group.get("cards", []):
                    node_ids.update(card.get("filters", {}).keys())

        if not node_ids:
            return

        for node in Node.objects.filter(pk__in=node_ids).select_related(
            "graph", "nodegroup"
        ):
            self._nodes[str(node.nodeid)] = node

    def _cache_key(self, data: dict[str, Any]) -> str:
        """Generate a unique cache key for the search parameters."""

        raw = {
            "result_operation": data.get("result_operation", "intersect"),
            "sections": data.get("sections", []),
            "translate_mode": data.get("translate_mode", TranslateMode.NONE),
            "user_id": self.request.user.id,
        }

        return f"cross_model_search_{hashlib.md5(str(raw).encode()).hexdigest()}"

    def _compute_target_ids(
        self,
        sections: list[dict[str, Any]],
        target_graph: str,
        operation: str,
    ) -> set[str]:
        """Compute target IDs using cache or fresh computation."""

        key = self._cache_key(self._data)
        cached = cache.get(key)

        if cached is not None:
            return set(cached)

        if not LinkCache._ready:
            LinkCache._init()

        engine = SearchEngineFactory().create()
        scroller = Scroller(engine)
        factory = DataTypeFactory()
        linker = Linker()

        intersector = Intersector(factory, linker, self._nodes, self.request, scroller)
        target_ids = intersector.compute(sections, target_graph, operation)

        cache.set(key, list(target_ids), CACHE_TIMEOUT)

        return target_ids

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

    def _get_target(self) -> list[dict[str, Any]]:
        """
        Build the list of available intersection targets for the UI.

        Only active resource graphs are included. System settings graphs and
        graphs derived from a source identifier (i.e. branches) are excluded.
        Graphs are sorted alphabetically by name.
        """

        if not LinkCache._ready:
            LinkCache._init()

        graphs = (
            GraphModel.objects.filter(is_active=True, isresource=True)
            .exclude(pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
            .exclude(source_identifier__isnull=False)
            .only("graphid", "name", "slug")
        )

        result = []

        for graph in graphs:
            graph_id = str(graph.graphid)
            name = graph.name

            if isinstance(name, dict):
                name = name.get("en", list(name.values())[0] if name else graph.slug)

            result.append(
                {
                    "graph_id": graph_id,
                    "label": f"Intersect to {name}",
                    "name": name,
                    "slug": graph.slug,
                }
            )

        result.sort(key=lambda x: (x["name"] or "").lower())

        return result

    def _is_valid(self, value: Any) -> bool:
        """Check if a filter value is valid (non-empty, allowing 0 and False)."""

        if not value:
            return False

        if isinstance(value, dict):
            val = value.get("val", "")
            return bool(val) or val == 0 or val is False

        return True

    def append_dsl(self, query_obj: dict[str, Any], **kwargs: Any) -> None:
        """
        Append the cross-model filter to the main Elasticsearch query object.

        In raw mode, each section's query is wrapped in a graph_id filter and
        combined with OR so results from any matching model are returned.

        In intersection mode, Intersector.compute() resolves the target IDs and
        they are injected as a terms filter. If no IDs are found, an impossible
        filter (a terms clause with a sentinel value) is added to guarantee an
        empty result set rather than an unfiltered one.
        """

        param = kwargs.get("querystring", "{}")
        data = (
            JSONDeserializer().deserialize(param)
            if isinstance(param, str)
            else param or {}
        )

        self._data = data
        self._target_ids = None

        if not data:
            return

        sections = data.get("sections", [])
        mode = data.get("translate_mode", TranslateMode.NONE)
        operation = data.get("result_operation", "intersect")

        if not sections:
            return

        self._build_cache(sections)

        # Intersection mode: compute target IDs and filter to them
        if mode != TranslateMode.NONE:
            target_graph = self._get_graph_id(mode)

            if not target_graph:
                return

            target_ids = self._compute_target_ids(sections, target_graph, operation)
            self._target_ids = target_ids

            if target_ids:
                id_filter = Bool()
                id_filter.filter(
                    Terms(field="resourceinstanceid", terms=list(target_ids))
                )
                query_obj["query"].add_query(id_filter)
            else:
                # No matches - use impossible filter to return empty results
                id_filter = Bool()
                id_filter.filter(
                    Terms(field="resourceinstanceid", terms=["__no_match__"])
                )
                query_obj["query"].add_query(id_filter)

            return

        # Raw mode: combine all section queries with OR
        factory = DataTypeFactory()
        cross_query = Bool()

        for section_data in sections:
            section = SectionFilter.create(section_data)

            if not section.graph:
                continue

            section_query = section.build(factory, self._nodes, self.request)

            if not has_clause(section_query):
                continue

            # Each section is a separate OR branch
            graph_filter = Bool()
            graph_filter.filter(Terms(field="graph_id", terms=[section.graph]))
            graph_filter.must(section_query)

            cross_query.should(graph_filter)

        if cross_query.dsl["bool"]["should"]:
            cross_query.dsl["bool"]["minimum_should_match"] = 1

        if has_clause(cross_query):
            query_obj["query"].add_query(cross_query)

    def post_search_hook(
        self,
        query_obj: dict[str, Any],
        response: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Post-search processing hook (not currently used)."""

        pass

    def view_data(self) -> dict[str, Any]:
        """
        Return the data required to populate the frontend search component.

        Cards are filtered to those the requesting user has read permission on,
        so the sidebar only shows nodegroups the user can actually query.
        System settings graphs, inactive graphs, and branch graphs are excluded
        from the graph list. Graphs are sorted alphabetically by their English
        name to provide a consistent ordering in the UI.
        """

        resource_graphs = (
            GraphModel.objects.exclude(pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
            .exclude(isresource=False)
            .exclude(is_active=False)
            .exclude(source_identifier__isnull=False)
        )

        searchable_datatypes = [
            dt.pk for dt in DDataType.objects.filter(issearchable=True)
        ]

        searchable_nodes = Node.objects.filter(
            datatype__in=searchable_datatypes,
            graph__is_active=True,
            graph__isresource=True,
            issearchable=True,
        ).select_related("graph", "nodegroup")

        resource_cards = CardModel.objects.filter(
            graph__is_active=True,
            graph__isresource=True,
        ).select_related("graph", "nodegroup")

        # Only include cards the user has permission to read
        searchable_cards = [
            card
            for card in resource_cards
            if self.request.user.has_perm("read_nodegroup", card.nodegroup)
        ]

        # Sort graphs alphabetically by name
        sorted_graphs = sorted(
            resource_graphs,
            key=lambda graph: (
                graph.name.get("en", "")
                if isinstance(graph.name, dict)
                else (graph.name or "")
            ).lower(),
        )

        return {
            "cardwidgets": CardXNodeXWidget.objects.filter(
                node__in=searchable_nodes,
            ).select_related("card", "node", "widget"),
            "cards": searchable_cards,
            "datatypes": DDataType.objects.all(),
            "graphs": sorted_graphs,
            "intersection_targets": self._get_target(),
            "nodes": searchable_nodes,
        }
