import json

from arches.app.search.components.base import BaseSearchFilter
from arches.app.search.elasticsearch_dsl_builder import Bool, Ids

details = {
    "searchcomponentid": "f0e0c7d8-a9b8-4567-cdef-123456789abc",
    "name": "Resource IDs Filter",
    "icon": "",
    "modulename": "ids_filter.py",
    "classname": "IdsFilter",
    "type": "filter",
    "componentpath": "",
    "componentname": "ids",
    "sortorder": "0",
    "enabled": True,
}


class IdsFilter(BaseSearchFilter):
    def append_dsl(self, search_query_object, **kwargs):
        querystring = kwargs.get("querystring", None)

        if not querystring:
            return

        try:
            resource_ids = json.loads(querystring)
        except (json.JSONDecodeError, TypeError):
            return

        if not resource_ids or not isinstance(resource_ids, list):
            return

        ids_query = Bool()
        ids_query.filter(Ids(ids=resource_ids))
        search_query_object["query"].add_query(ids_query)
