"""Resources hanging off a set of parent resources, by the link each graph uses
to point back at its parent."""

from arches.app.models.models import ResourceXResource

from arches_querysets.models import ResourceTileTree

from bcap.util.bcap_aliases import GraphSlugs


class RelatedResourceService:
    """Reads the children of given parents for the site record's related tabs."""

    @staticmethod
    def base_query(graph_slug, resource_ids):
        """The rows hanging off these parents: a site by its parent_site, a
        publication through the reference table, every other graph by its
        archaeological_site link. Staff-only route, so no narrowing by caller."""
        ids = [str(resource_id) for resource_id in resource_ids]
        queryset = ResourceTileTree.get_tiles(
            graph_slug, as_representation=True
        ).select_related("graph", "resource_instance_lifecycle_state")

        if graph_slug == GraphSlugs.ARCHAEOLOGICAL_SITE:
            return queryset.filter(parent_site__id__in=ids)
        if graph_slug == GraphSlugs.PUBLICATION:
            publication_ids = ResourceXResource.objects.filter(
                from_resource_id__in=ids
            ).values("to_resource_id")
            return queryset.filter(resourceinstanceid__in=publication_ids)
        return queryset.filter(archaeological_site__id__in=ids)
