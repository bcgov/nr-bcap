"""Bulk Elasticsearch indexing: index several resources in one request instead
of one round-trip each. Resource.index() also rebuilds the datatype factory and
serialized graph on every call, so for a handful of resources this is several
times faster."""

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models import models
from arches.app.models.resource import Resource
from arches.app.search.mappings import RESOURCES_INDEX, TERMS_INDEX
from arches.app.search.search_engine_factory import SearchEngineFactory


def bulk_index(resources):
    """Index the given (already-saved) resources in one bulk request rather than
    one Elasticsearch round-trip per resource. Each is re-fetched as a core
    Resource so get_documents_to_index() is available and reads fresh state,
    accepting either core Resource or arches-querysets resources."""
    se = SearchEngineFactory().create()
    datatype_factory = DataTypeFactory()
    node_datatypes = {
        str(nodeid): datatype
        for nodeid, datatype in models.Node.objects.values_list("nodeid", "datatype")
    }

    def bulk_items(resource):
        """The resource's search document plus its term documents, as ES bulk items."""
        document, terms = resource.get_documents_to_index(
            datatype_factory=datatype_factory, node_datatypes=node_datatypes
        )
        document["root_ontology_class"] = resource.get_root_ontology()
        yield se.create_bulk_item(
            index=RESOURCES_INDEX, id=document["resourceinstanceid"], data=document
        )
        for term in terms:
            yield se.create_bulk_item(
                index=TERMS_INDEX, id=term["_id"], data=term["_source"]
            )

    se.bulk_index(
        item for r in resources for item in bulk_items(Resource.objects.get(pk=r.pk))
    )
