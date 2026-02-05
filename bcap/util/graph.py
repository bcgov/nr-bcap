from arches.app.models import models


def get_current_graph(slug: str) -> models.GraphModel | None:
    return models.GraphModel.objects.filter(
        slug=slug, source_identifier_id__isnull=True
    ).first()
