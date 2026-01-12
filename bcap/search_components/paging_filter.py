from arches.app.models.system_settings import settings
from arches.app.search.components.base import BaseSearchFilter
from arches.app.utils.pagination import get_paginator

details = {
    "searchcomponentid": "7aff5819-651c-4390-9b9a-a61221ba52c6",
    "name": "Paging",
    "icon": "",
    "modulename": "paging_filter.py",
    "classname": "PagingFilter",
    "type": "paging-filter-type",
    "componentpath": "views/components/search/paging-filter",
    "componentname": "paging-filter",
    "config": {},
}


class PagingFilter(BaseSearchFilter):

    def _get_param(self, name: str, default=None):
        value = self.request.GET.get(name)
        if value is None:
            value = self.request.POST.get(name)
        if value is None:
            return default
        return value

    def append_dsl(self, search_query_object, **kwargs):
        export = self._get_param("export")
        mobile_download = self._get_param("mobiledownload")
        page_param = self._get_param(self.componentname, "1")
        page = 1 if page_param == "" else int(page_param)

        if export is not None:
            limit = settings.SEARCH_RESULT_LIMIT
        elif mobile_download is not None:
            limit = self._get_param("resourcecount")
        else:
            limit = settings.SEARCH_ITEMS_PER_PAGE
        limit = int(self._get_param("limit", limit))
        search_query_object["query"].start = limit * int(page - 1)
        search_query_object["query"].limit = limit

    def post_search_hook(self, search_query_object, response_object, **kwargs):
        total = (
            response_object["results"]["hits"]["total"]["value"]
            if response_object["results"]["hits"]["total"]["value"]
            <= settings.SEARCH_RESULT_LIMIT
            else settings.SEARCH_RESULT_LIMIT
        )
        page_param = self._get_param(self.componentname, "1")
        page = 1 if page_param == "" else int(page_param)

        paginator, pages = get_paginator(
            self.request,
            response_object["results"],
            total,
            page,
            settings.SEARCH_ITEMS_PER_PAGE,
        )
        page = paginator.page(page)

        ret = {}
        ret["current_page"] = page.number
        ret["has_next"] = page.has_next()
        ret["has_previous"] = page.has_previous()
        ret["has_other_pages"] = page.has_other_pages()
        ret["next_page_number"] = page.next_page_number() if page.has_next() else None
        ret["previous_page_number"] = (
            page.previous_page_number() if page.has_previous() else None
        )
        ret["start_index"] = page.start_index()
        ret["end_index"] = page.end_index()
        ret["pages"] = pages

        if self.componentname not in response_object:
            response_object[self.componentname] = {}
        response_object[self.componentname]["paginator"] = ret
