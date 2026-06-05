from bcap.util.bcap_aliases import AbstractAliases


class ProcessRequirementAliases(AbstractAliases):
    ASSESSMENT_NOTES = "assessment_notes"
    DEFAULT_TARGET_PROCESSING_TIME = "default_target_processing_time"
    HAS_SUBMISSION_REQUIREMENT = "has_submission_requirement"
    IS_INTERNAL_REQUIREMENT = "is_internal_requirement"
    IS_TEMPLATE_REQUIREMENT = "is_template_requirement"
    REQUIREMENT_IDENTIFICATION = "requirement_identification"
    REQUIREMENT_NAME = "requirement_name"
    REQUIREMENT_PROCESS_COMPLETION_DATE = "requirement_process_completion_date"
    REQUIREMENT_PROCESS_DUE_DATE = "requirement_process_due_date"
    REQUIREMENT_PROCESS_START_DATE = "requirement_process_start_date"
    REQUIREMENT_STATUS = "requirement_status"
    REQUIREMENT_SUBMISSION = "requirement_submission"
    SUB_REQUIREMENT_ASSESSMENT_NOTES = "sub_requirement_assessment_notes"
    SUB_REQUIREMENT_DESCRIPTION = "sub_requirement_description"
    SUB_REQUIREMENT_MANDATORY = "sub_requirement_mandatory"
    SUB_REQUIREMENT_NAME = "sub_requirement_name"
    SUB_REQUIREMENT_SATISFIED = "sub_requirement_satisfied"
    SUB_REQUIREMENT_SORT_ORDER = "sub_requirement_sort_order"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(ProcessRequirementAliases)


class ProcessRequirementGroupAliases(AbstractAliases):
    REQUIREMENT_EXECUTION_DURATION = "requirement_execution_duration"
    SUB_REQUIREMENT = "sub_requirement"
    SUB_REQUIREMENT_ASSESSMENT_N1 = "sub_requirement_assessment_n1"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(ProcessRequirementGroupAliases)
