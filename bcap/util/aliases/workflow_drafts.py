from bcap.util.bcap_aliases import AbstractAliases


class WorkflowDraftsAliases(AbstractAliases):
    CURRENT_STEP = "current_step"
    DRAFT_DATA = "draft_data"
    DRAFT_SESSION_ID = "draft_session_id"
    FRONTEND_VERSION = "frontend_version"
    GRAPH_PUBLICATION_ID = "graph_publication_id"
    GRAPH_SLUG = "graph_slug"
    OWNING_ORGANIZATION = "owning_organization"
    PARENT_RESOURCE = "parent_resource"
    SECTION = "section"
    UPDATED_DATE = "updated_date"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(WorkflowDraftsAliases)


class WorkflowDraftsGroupAliases(AbstractAliases):
    DRAFT_PAYLOAD = "draft_payload"
    FILING_INFO = "filing_info"
    SYSTEM_INFO = "system_info"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(WorkflowDraftsGroupAliases)
