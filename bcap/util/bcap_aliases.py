# Classes to standardize the resource model node aliases
class AbstractAliases:
    @staticmethod
    def get_dict(cls):
        newdict = {
            k: v
            for k, v in cls.__dict__.items()
            if not k.startswith("_") and not k == "get_aliases"
        }
        return newdict


class BCAPSiteAliases(AbstractAliases):
    ACCURACY_REMARKS = 'accuracy_remarks'
    ADDRESS_REMARKS = 'address_remarks'
    ALERT_BRANCH_CONTACT = 'alert_branch_contact'
    ALERT_DETAILS = 'alert_details'
    ALERT_ENTERED_BY = 'alert_entered_by'
    ALERT_ENTRY_DATE = 'alert_entry_date'
    ALERT_SUBJECT = 'alert_subject'
    ANCESTRAL_REMAINS = 'ancestral_remains'
    ARCHAEOLOGICAL_DATA = 'archaeological_data'
    AUTHORITY = 'authority'
    AUTHORITY_DESCRIPTION = 'authority_description'
    AUTHORITY_EFFECTIVE_PERIOD = 'authority_effective_period'
    AUTHORITY_END_DATE = 'authority_end_date'
    AUTHORITY_START_DATE = 'authority_start_date'
    BCAP_SUBMISSION_STATUS = 'bcap_submission_status'
    BC_HERITAGE_RESOURCE = 'bc_heritage_resource'
    BC_PROPERTY_ADDRESS = 'bc_property_address'
    BC_PROPERTY_LEGAL_DESCRIPTION = 'bc_property_legal_description'
    BC_RIGHT = 'bc_right'
    BIOGEOGRAPHY_DESCRIPTION = 'biogeography_description'
    BIOGEOGRAPHY_NAME = 'biogeography_name'
    BIOGEOGRAPHY_TYPE = 'biogeography_type'
    BORDEN_NUMBER = 'borden_number'
    CITY = 'city'
    COPYRIGHT = 'copyright'
    DECISION_CRITERIA = 'decision_criteria'
    DECISION_DATE = 'decision_date'
    DECISION_DESCRIPTION = 'decision_description'
    DECISION_MADE_BY = 'decision_made_by'
    DESIGNATION_OR_PROTECTION_END_DATE = 'designation_or_protection_end_date'
    DESIGNATION_OR_PROTECTION_START_DATE = 'designation_or_protection_start_date'
    DOCUMENT_DESCRIPTION = 'document_description'
    DOCUMENT_TYPE = 'document_type'
    ELEVATION = 'elevation'
    ELEVATION_COMMENTS = 'elevation_comments'
    EXTERNAL_URL = 'external_url'
    EXTERNAL_URL_TYPE = 'external_url_type'
    GIS_ELEVATION_RANGE = 'gis_elevation_range'
    GIS_LOWER_ELEVATION = 'gis_lower_elevation'
    GIS_UPPER_ELEVATION = 'gis_upper_elevation'
    HERITAGE_SITE_LOCATION = 'heritage_site_location'
    HRIA_LEGACY_DATA = 'hria_legacy_data'
    IDENTIFICATION_AND_REGISTRATION = 'identification_and_registration'
    IMAGE_DATE = 'image_date'
    IMAGE_DESCRIPTION = 'image_description'
    IMAGE_FEATURES = 'image_features'
    IMAGE_TYPE = 'image_type'
    IMAGE_VIEW = 'image_view'
    INTERNAL_REMARK = 'internal_remark'
    LATEST_EDIT_TYPE = 'latest_edit_type'
    LEGAL_ADDRESS_REMARKS = 'legal_address_remarks'
    LEGAL_DESCRIPTION = 'legal_description'
    LEGISLATIVE_ACT = 'legislative_act'
    LEGISLATIVE_ACT2 = 'legislative_act2'
    OFFICIALLY_RECOGNIZED_SITE = 'officially_recognized_site'
    PARENT_SITE = 'parent_site'
    PHOTOGRAPHER = 'photographer'
    PID = 'pid'
    PIN = 'pin'
    POSTAL_CODE = 'postal_code'
    PRIMARY_IMAGE = 'primary_image'
    PROTECTION_EVENT = 'protection_event'
    PROTECTION_NOTES = 'protection_notes'
    PUBLICATION_REFERENCE = 'publication_reference'
    RECOMMENDATION = 'recommendation'
    RECOMMENDATION_DATE = 'recommendation_date'
    RECOMMENDED_BY = 'recommended_by'
    REFERENCE_AUTHORS = 'reference_authors'
    REFERENCE_FILE = 'reference_file'
    REFERENCE_NUMBER = 'reference_number'
    REFERENCE_NUMBER2 = 'reference_number2'
    REFERENCE_REMARKS = 'reference_remarks'
    REFERENCES = 'references'
    REFERENCE_TITLE = 'reference_title'
    REFERENCE_TYPE = 'reference_type'
    REFERENCE_YEAR = 'reference_year'
    REGISTER_TYPE = 'register_type'
    REGISTRATION_DATE = 'registration_date'
    REGISTRATION_STATUS = 'registration_status'
    REGISTRY_TYPES2 = 'registry_types2'
    RELATED_DOCUMENTS = 'related_documents'
    REMARK_DATE = 'remark_date'
    REMARK_TYPE = 'remark_type'
    RESPONSIBLE_GOVERNMENT = 'responsible_government'
    RESPONSIBLE_GOVERNMENT2 = 'responsible_government2'
    RESTRICTED = 'restricted'
    SITE_BOUNDARY = 'site_boundary'
    SITE_DECISION = 'site_decision'
    SITE_IMAGES = 'site_images'
    SITE_RECORD_ADMIN = 'site_record_admin'
    SITE_SUBTYPE = 'site_subtype'
    SITE_TENURE = 'site_tenure'
    SITE_TENURE_IDENTIFIER = 'site_tenure_identifier'
    SITE_TENURE_REMARKS = 'site_tenure_remarks'
    SITE_TENURE_TYPE = 'site_tenure_type'
    SITE_TYPE = 'site_type'
    SITE_TYPOLOGY = 'site_typology'
    SOURCE_NOTES = 'source_notes'
    STREET_NAME = 'street_name'
    STREET_NUMBER = 'street_number'
    TIMESPAN_OF_DESIGNATION_OR_PROTECTION = 'timespan_of_designation_or_protection'
    TYPOLOGY_CLASS = 'typology_class'
    TYPOLOGY_DESCRIPTOR = 'typology_descriptor'

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(BCAPSiteAliases)


class BCAPSiteSubmissionAliases(AbstractAliases):
    SUBMITTING_GOVERNMENT = "submitting_government"
    SUBMISSION_DATE = "submission_date"
    SUBMITTED_SITE_COUNT = "total_number_submitted"
    HERITAGE_SITE = "archaeological_site"
    ASSIGNED_TO = "assigned_to"
    COMPLETION_DATE = "completion_date"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(BCAPSiteSubmissionAliases)


class BCAPLocalGovernmentAliases:
    TEST = "test"


class ContributorAliases(AbstractAliases):
    ASSOCIATED_ORGANIZATION = 'associated_organization'
    ASSOCIATION_PERIOD = 'association_period'
    CONTACT_EMAIL = 'contact_email'
    CONTACT_INFORMATION = 'contact_information'
    CONTACT_PHONE_NUMBER = 'contact_phone_number'
    CONTRIBUTOR = 'contributor'
    CONTRIBUTOR_NAME = 'contributor_name'
    CONTRIBUTOR_ROLE = 'contributor_role'
    CONTRIBUTOR_TYPE = 'contributor_type'
    END_DATE = 'end_date'
    FIRST_NAME = 'first_name'
    INACTIVE = 'inactive'
    NAME = 'name'
    PALEOLOGICAL_CONSULTANT = 'paleological_consultant'
    START_DATE = 'start_date'


class LegislativeActAliases(AbstractAliases):
    ACT_SECTION = "act_section"
    ACT_STATUS = "act_status"
    ACTIVE = "active"
    AUTHORITY = "authority"
    CITATION = "citation"
    DOCUMENT = "document"
    END_DATE = "end_date"
    LEGAL_INSTRUMENT = "legal_instrument"
    RECOGNITION_TYPE = "recognition_type"
    REPLACED_BY = "replaced_by"
    START_DATE = "start_date"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(LegislativeActAliases)


class GraphSlugs:
    HERITAGE_SITE = "archaeological_site"
    LEGISLATIVE_ACT = "legislative_act"
    SITE_SUBMISSION = "site_submission"
    SITE_VISIT = "site_visit"
