from bcap.util.bcap_aliases import AbstractAliases


class PermitApplicationAliases(AbstractAliases):
    ALTERATION_DETAILS = "alteration_details"
    APPLICANT_NAME = "applicant_name"
    APPLICATION_ARCHAEOLOGIST = "application_archaeologist"
    APPLICATION_ID = "application_id"
    APPLICATION_PRIORITY_LEVEL = "application_priority_level"
    APPLICATION_PROPONENT = "application_proponent"
    APPLICATION_SUBMISSION_DATE = "application_submission_date"
    APPROACH_ON_CONCURRENT_PERMITS = "approach_on_concurrent_permits"
    CONCURRENT_PERMITS_LIST = "concurrent_permits_list"
    COPYRIGHT_AUTHORIZATION = "copyright_authorization"
    FN_FILE_NUMBERS = "fn_file_numbers"
    GRANT_OF_LICENSE_TO_MINISTRY = "grant_of_license_to_ministry"
    HAS_CONCURRENT_PERMITS = "has_concurrent_permits"
    HAS_FN_ENDORSEMENTS = "has_fn_endorsements"
    HAS_RETAINED_ARCHAEOLOGIST = "has_retained_archaeologist"
    INDUSTRIAL_SECTOR = "industrial_sector"
    IS_CONSENT_GIVEN = "is_consent_given"
    IS_RELATED_PERMIT = "is_related_permit"
    IS_REPLACEMENT = "is_replacement"
    MAP_OR_HIP = "map_or_hip"
    MINISTRY_ASSIGNEE = "ministry_assignee"
    MZA_ALTERATION_DETAILS = "mza_alteration_details"
    MZA_INDUSTRIAL_SECTOR = "mza_industrial_sector"
    MZA_PROJECT_BOUNDARY = "mza_project_boundary"
    MZA_PROJECT_DESCRIPTION = "mza_project_description"
    MZA_PROJECT_TYPE = "mza_project_type"
    MZA_REQUIREMENT = "mza_requirement"
    MZA_REQUIREMENT_MINISTRY_ASIGNEE = "mza_requirement_ministry_asignee"
    MZA_SCOPE_OF_WORK = "mza_scope_of_work"
    PERMIT_DURATION_YEARS_REQUESTED = "permit_duration_years_requested"
    PERMIT_MESSAGES = "permit_messages"
    PROCESS_REQUIREMENT = "process_requirement"
    PROCESS_REQUIREMENT_ORDER = "process_requirement_order"
    PROJECT_BOUNDARY = "project_boundary"
    PROJECT_DESCRIPTION = "project_description"
    PROJECT_NAME = "project_name"
    PROJECT_OFFICER = "project_officer"
    PROJECT_TYPE = "project_type"
    RATIONALE_FOR_NO_ARCHAEOLOGIST = "rationale_for_no_archaeologist"
    RELATED_PERMIT = "related_permit"
    RESPONSIBLE_EXTERNAL_ARCHAEOLOGIST = "responsible_external_archaeologist"
    SCOPE_OF_WORK = "scope_of_work"
    SUPPLEMENTAL_INFORMATION = "supplemental_information"
    TIME_OF_CONSENT = "time_of_consent"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(PermitApplicationAliases)


class PermitApplicationGroupAliases(AbstractAliases):
    APPLICATION_ADMIN = "application_admin"
    APPLICATION_CONTACTS = "application_contacts"
    APPLICATION_IDENTIFICATION = "application_identification"
    ARCHAEOLOGICAL_ASSESSMENT_PLAN = "archaeological_assessment_plan"
    DEVELOPMENT_PROJECT_DETAILS = "development_project_details"
    FIRST_NATIONS_CONSULTATION = "first_nations_consultation"
    LEGAL_AND_CONSENT = "legal_and_consent"
    MULTI_ZONE_AREA_ADDITION = "multi_zone_area_addition"
    MZA_PROJECT_DETAILS = "mza_project_details"
    PROPOSED_PROJECT = "proposed_project"
    PROPOSED_PROJECT_N1 = "proposed_project_n1"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(PermitApplicationGroupAliases)
