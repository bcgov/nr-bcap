from bcap.util.bcap_aliases import AbstractAliases


class ProjectEngagementAliases(AbstractAliases):
    CONTRIBUTOR_REFERENCE = "contributor_reference"
    ENGAGEMENT_DOCUMENT = "engagement_document"
    ENGAGEMENT_END_DATE = "engagement_end_date"
    ENGAGEMENT_OUTCOME_SUMMARY = "engagement_outcome_summary"
    ENGAGEMENT_START_DATE = "engagement_start_date"
    ENGAGEMENT_STATUS = "engagement_status"
    ENGAGEMENT_STEPS_TAKEN = "engagement_steps_taken"
    ENGAGEMENT_TARGET_LENGTH = "engagement_target_length"
    ENGAGEMENT_TYPE = "engagement_type"
    IS_MANDATORY = "is_mandatory"
    OTHER_PARTICIPANT = "other_participant"
    PACKAGE_CONFIRMATION_FILES = "package_confirmation_files"
    PACKAGE_DELIVERY_DATE = "package_delivery_date"
    PACKAGE_DELIVERY_METHOD = "package_delivery_method"
    PACKAGE_DELIVERY_NOTES = "package_delivery_notes"
    PACKAGE_DELIVERY_STATUS = "package_delivery_status"
    PACKAGE_DOCUMENTS = "package_documents"
    PACKAGE_TARGET_DELIVERY_DATE = "package_target_delivery_date"
    PARTICIPANT_EMAIL_ADDRESS = "participant_email_address"
    PARTICIPANT_NOTES = "participant_notes"
    PARTICIPANT_PHONE_NUMBER = "participant_phone_number"
    PARTICIPANT_PORTAL_URL = "participant_portal_url"
    PARTICIPANT_ROLE = "participant_role"
    PARTICIPANT_TYPE = "participant_type"
    SHOULD_BE_DELIVERED = "should_be_delivered"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(ProjectEngagementAliases)


class ProjectEngagementGroupAliases(AbstractAliases):
    ENGAGEMENT = "engagement"
    ENGAGEMENT_DETAILS = "engagement_details"
    ENGAGEMENT_PARTICIPANT = "engagement_participant"
    REFERRAL_PACKAGE = "referral_package"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(ProjectEngagementGroupAliases)
