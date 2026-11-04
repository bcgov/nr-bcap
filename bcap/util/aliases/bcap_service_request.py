from bcap.util.bcap_aliases import AbstractAliases


class BcapServiceRequestAliases(AbstractAliases):
    APPLICATION_ARCHAEOLOGIST = "application_archaeologist"
    APPLICATION_PROPONENT = "application_proponent"
    APPLICATION_SUBMISSION_DATE = "application_submission_date"
    FILING_TYPE = "filing_type"
    HAS_RETAINED_ARCHAEOLOGIST = "has_retained_archaeologist"
    IS_MODULE_COMPLETED = "is_module_completed"
    MINISTRY_ASSIGNEE = "ministry_assignee"
    MINISTRY_ASSIGNEE_N1 = "ministry_assignee_n1"
    MODULE_COMPLETED_DATE = "module_completed_date"
    MODULE_ID = "module_id"
    MODULE_NAME = "module_name"
    MODULE_ORDER = "module_order"
    PROCESS_REQUIREMENT = "process_requirement"
    PROCESS_REQUIREMENT_ORDER = "process_requirement_order"
    PROJECT_BOUNDARY = "project_boundary"
    PROJECT_DESCRIPTION = "project_description"
    PROJECT_NAME = "project_name"
    PROJECT_TYPE = "project_type"
    RATIONALE_FOR_NO_ARCHAEOLOGIST = "rationale_for_no_archaeologist"
    SCOPE_OF_WORK = "scope_of_work"
    SERVICE_REQUEST_COMPLETION_TARGET = "service_request_completion_target"
    SERVICE_REQUEST_ID = "service_request_id"
    SERVICE_REQUEST_MESSAGES = "service_request_messages"
    SUPPLEMENTAL_INFORMATION = "supplemental_information"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(BcapServiceRequestAliases)


class BcapServiceRequestGroupAliases(AbstractAliases):
    PROCESS_MODULE = "process_module"
    PROPOSED_PROJECT = "proposed_project"
    SERVICE_REQUEST_ADMIN = "service_request_admin"
    SERVICE_REQUEST_CONTACTS = "service_request_contacts"
    SERVICE_REQUEST_IDENTIFICATION = "service_request_identification"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(BcapServiceRequestGroupAliases)
