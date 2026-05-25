from bcap.util.bcap_aliases import AbstractAliases


class ProcessRequirementAliases(AbstractAliases):
    # Partial subset of the process_requirement graph: only the nodes the
    # dashboard reads. Extend as more of the graph gets consumed.
    REQUIREMENT_NAME = "requirement_name"
    REQUIREMENT_PROCESS_DUE_DATE = "requirement_process_due_date"
    REQUIREMENT_STATUS = "requirement_status"
    ASSESSMENT_NOTES = "assessment_notes"
    SUB_REQUIREMENT = "sub_requirement"
    SUB_REQUIREMENT_SATISFIED = "sub_requirement_satisfied"
    SUB_REQUIREMENT_SORT_ORDER = "sub_requirement_sort_order"
    SUB_REQUIREMENT_ASSESSMENT_NOTES = "sub_requirement_assessment_notes"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(ProcessRequirementAliases)
