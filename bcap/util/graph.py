from arches.app.models import models


def get_current_graph(slug: str) -> models.GraphModel | None:
    return models.GraphModel.objects.filter(
        slug=slug, source_identifier_id__isnull=True
    ).first()


def get_node(graph_slug: str, alias: str) -> models.Node:
    """The published (non-draft) node with this alias on the given graph."""
    return models.Node.objects.get(
        graph__slug=graph_slug, alias=alias, source_identifier=None
    )
