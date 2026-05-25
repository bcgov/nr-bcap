from bcap.util.bcap_aliases import AbstractAliases


class PermitApplicationAliases(AbstractAliases):
    # Partial subset of the permit_application graph: only the nodes the
    # dashboard reads. Extend as more of the graph gets consumed.
    APPLICATION_ID = "application_id"
    APPLICATION_PRIORITY_LEVEL = "application_priority_level"
    INDUSTRIAL_SECTOR = "industrial_sector"
    MINISTRY_ASSIGNEE = "ministry_assignee"
    PROCESS_REQUIREMENT = "process_requirement"
    PROCESS_REQUIREMENT_ORDER = "process_requirement_order"
    PROJECT_NAME = "project_name"
    RELATED_PERMIT = "related_permit"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(PermitApplicationAliases)
