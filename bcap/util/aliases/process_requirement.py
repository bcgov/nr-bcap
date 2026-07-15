from bcap.util.bcap_aliases import AbstractAliases


class ProcessRequirementAliases(AbstractAliases):
    ASSESSMENT_NOTES = "assessment_notes"
    CHECKLIST_ITEM_ASSESSMENT_NOTES = "checklist_item_assessment_notes"
    CHECKLIST_ITEM_COMPLETED = "checklist_item_completed"
    CHECKLIST_ITEM_DESCRIPTION = "checklist_item_description"
    CHECKLIST_ITEM_MANDATORY = "checklist_item_mandatory"
    CHECKLIST_ITEM_NAME = "checklist_item_name"
    CHECKLIST_ITEM_SORT_ORDER = "checklist_item_sort_order"
    DEFAULT_TARGET_PROCESSING_TIME = "default_target_processing_time"
    IS_INTERNAL_REQUIREMENT = "is_internal_requirement"
    IS_TEMPLATE_REQUIREMENT = "is_template_requirement"
    PARENT_MODULE = "parent_module"
    PARENT_REQUIREMENT = "parent_requirement"
    PROCESS_REQUIREMENT_TYPE = "process_requirement_type"
    REQUIREMENT_IDENTIFICATION = "requirement_identification"
    REQUIREMENT_NAME = "requirement_name"
    REQUIREMENT_PROCESS_COMPLETION_DATE = "requirement_process_completion_date"
    REQUIREMENT_PROCESS_DUE_DATE = "requirement_process_due_date"
    REQUIREMENT_PROCESS_START_DATE = "requirement_process_start_date"
    REQUIREMENT_STATUS = "requirement_status"
    SUBMISSION_DATA = "submission_data"
    WORKFLOW_URL = "workflow_url"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(ProcessRequirementAliases)


class ProcessRequirementGroupAliases(AbstractAliases):
    REQUIREMENT_DATA = "requirement_data"
    REQUIREMENT_EXECUTION_DURATION = "requirement_execution_duration"
    SUB_REQUIREMENT_ASSESSMENT_N1 = "sub_requirement_assessment_n1"
    SUB_REQUIREMENT_N1 = "sub_requirement_n1"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(ProcessRequirementGroupAliases)
