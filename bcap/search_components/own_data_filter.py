from arches.app.search.components.base import BaseSearchFilter

details = {
    "searchcomponentid": "",
    "name": "Own Data Filter",
    "icon": "",
    "modulename": "own_data_filter.py",
    "classname": "OwnDataFilter",
    # popup shows icon on RHS of search header, "filter" shows as a tab, "" doesn't show
    "type": "",
    "componentpath": "views/components/search/own-data-filter",
    "componentname": "own-data-filter",
    "sortorder": "0",
    "enabled": True,
}


class OwnDataFilter(BaseSearchFilter):
    def user_in_group(self, group_name):
        return self.request.user.groups.filter(name=group_name).exists()

    def append_dsl(
        self, search_results_object, permitted_nodegroups, include_provisional
    ):
        if self.user_in_group("Local Government"):
            print("\tUser in Local Government... filter")
        else:
            print("\tNo Local Government Filter applied")
