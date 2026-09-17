import uuid

from django.core.cache import cache

from arches.app.models import models
from arches.app.utils.betterJSONSerializer import JSONDeserializer


def get_current_graph(slug: str) -> models.GraphModel | None:
    return models.GraphModel.objects.filter(
        slug=slug, source_identifier_id__isnull=True
    ).first()


def get_node(graph_slug: str, alias: str) -> models.Node:
    """The published (non-draft) node with this alias on the given graph. Use
    when the Node object is needed (e.g. its config); node_id is cached."""
    return models.Node.objects.get(
        graph__slug=graph_slug, alias=alias, source_identifier=None
    )


def nodes_for(graph_slug, aliases):
    """Node queryset for the given aliases, shaped to pass as the nodes argument
    to get_tiles."""
    return (
        models.Node.objects.filter(
            graph__slug=graph_slug,
            source_identifier=None,
            alias__in=aliases,
        )
        .exclude(datatype="semantic")
        .exclude(nodegroup=None)
        .select_related("nodegroup__parentnodegroup")
    )


def _graph_nodes(graph_slug):
    """Every node of a graph's published copy as {alias: (nodeid, nodegroup_id)},
    cached by publication so a republish or reload is picked up on the next
    request without a server restart."""
    publication_id = (
        models.GraphModel.objects.filter(slug=graph_slug, source_identifier=None)
        .values_list("publication_id", flat=True)
        .first()
    )
    cache_key = f"bcap:graph_nodes:{graph_slug}:{publication_id}"
    nodes = cache.get(cache_key)
    if nodes is None:
        nodes = {
            node["alias"]: (str(node["nodeid"]), str(node["nodegroup_id"]))
            for node in models.Node.objects.filter(
                graph__slug=graph_slug, source_identifier=None
            ).values("alias", "nodeid", "nodegroup_id")
        }
        cache.set(cache_key, nodes, timeout=300)
    return nodes


def node_info(graph_slug, alias):
    """(nodeid, nodegroup_id) as strings for a graph's node alias."""
    return _graph_nodes(graph_slug)[alias]


def node_id(graph_slug, alias):
    """nodeid as a string for a graph's node alias."""
    return node_info(graph_slug, alias)[0]


def nodegroup_id(graph_slug, alias):
    """nodegroup_id as a string for a graph's node alias."""
    return node_info(graph_slug, alias)[1]


def relatable_graph_slugs(graph_slug, alias):
    """The graph slugs a resource-instance node offers, empty for any other
    node."""
    node = models.Node.objects.filter(
        graph__slug=graph_slug, alias=alias, source_identifier=None
    ).first()
    config = JSONDeserializer().deserialize(node.config.value) if node else {}
    return frozenset(
        models.GraphModel.objects.filter(
            pk__in=[entry["graphid"] for entry in config.get("graphs", [])]
        ).values_list("slug", flat=True)
    )


def graph_slugs_of(resource_ids):
    """The graph slugs these resource ids belong to. Anything that is not a uuid
    is dropped rather than raised on, since it matches no resource either."""
    ids = []
    for value in resource_ids:
        try:
            ids.append(uuid.UUID(str(value)))
        except ValueError:
            continue
    return frozenset(
        models.ResourceInstance.objects.filter(pk__in=ids).values_list(
            "graph__slug", flat=True
        )
    )
