from bcap.util.bcap_aliases import AbstractAliases


class BcapServiceRequestAliases(AbstractAliases):
    ADDRESS_REMARKS = "address_remarks"
    APPLICATION_ARCHAEOLOGIST = "application_archaeologist"
    APPLICATION_PROPONENT = "application_proponent"
    APPLICATION_SUBMISSION_DATE = "application_submission_date"
    CITY = "city"
    CROWN_LAND_TENURE_TYPE = "crown_land_tenure_type"
    DISTRICTS = "districts"
    HAS_RETAINED_ARCHAEOLOGIST = "has_retained_archaeologist"
    IS_MODULE_COMPLETED = "is_module_completed"
    LAND_TITLE = "land_title"
    LEGAL_ADDRESS_REMARKS = "legal_address_remarks"
    LEGAL_DESCRIPTION = "legal_description"
    MINISTRY_ASSIGNEE = "ministry_assignee"
    MINISTRY_ASSIGNEE_N1 = "ministry_assignee_n1"
    MODULE_COMPLETED_DATE = "module_completed_date"
    MODULE_ID = "module_id"
    MODULE_NAME = "module_name"
    MODULE_ORDER = "module_order"
    PID = "pid"
    PIN = "pin"
    PIN_N1 = "pin_n1"
    POSTAL_CODE = "postal_code"
    PROCESS_REQUIREMENT = "process_requirement"
    PROCESS_REQUIREMENT_ORDER = "process_requirement_order"
    PROJECT_DESCRIPTION = "project_description"
    PROJECT_NAME = "project_name"
    PROJECT_TYPE = "project_type"
    RATIONALE_FOR_NO_ARCHAEOLOGIST = "rationale_for_no_archaeologist"
    SCOPE_OF_WORK = "scope_of_work"
    SERVICE_REQUEST_BOUNDARY = "service_request_boundary"
    SERVICE_REQUEST_COMPLETION_TARGET = "service_request_completion_target"
    SERVICE_REQUEST_ID = "service_request_id"
    SERVICE_REQUEST_MESSAGES = "service_request_messages"
    SERVICE_REQUEST_TYPE = "service_request_type"
    STREET_NAME = "street_name"
    STREET_NUMBER = "street_number"
    TENURE_DESCRIPTION = "tenure_description"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(BcapServiceRequestAliases)


class BcapServiceRequestGroupAliases(AbstractAliases):
    BC_PROPERTY_ADDRESS = "bc_property_address"
    BC_PROPERTY_LEGAL_DESCRIPTION = "bc_property_legal_description"
    CROWN_LAND_SURVEY_INFORMATION = "crown_land_survey_information"
    PROCESS_MODULE = "process_module"
    PROJECT_LOCATION = "project_location"
    PROPOSED_PROJECT = "proposed_project"
    SERVICE_REQUEST_ADMIN = "service_request_admin"
    SERVICE_REQUEST_CONTACTS = "service_request_contacts"
    SERVICE_REQUEST_IDENTIFICATION = "service_request_identification"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(BcapServiceRequestGroupAliases)
