from bcap.util.bcap_aliases import AbstractAliases


class DraftsAliases(AbstractAliases):
    DRAFT_DATA = "draft_data"
    FRONTEND_VERSION = "frontend_version"
    GRAPH_PUBLICATION_ID = "graph_publication_id"
    GRAPH_SLUG = "graph_slug"
    UPDATED_DATE = "updated_date"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(DraftsAliases)


class DraftsGroupAliases(AbstractAliases):

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(DraftsGroupAliases)
