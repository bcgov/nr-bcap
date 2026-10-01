from bcap.util.bcap_aliases import AbstractAliases


class ProjectEngagementAliases(AbstractAliases):
    ATTEMPT_RECIPIENT_CONTRIBUTOR_REFERENCE = "attempt_recipient_contributor_reference"
    ATTEMPT_RECIPIENT_EMAIL_ADDRESS = "attempt_recipient_email_address"
    ATTEMPT_RECIPIENT_NAME_AS_PROVIDED = "attempt_recipient_name_as_provided"
    ATTEMPT_RECIPIENT_PHONE_NUMBER = "attempt_recipient_phone_number"
    ATTEMPT_RECIPIENT_PORTAL_URL = "attempt_recipient_portal_url"
    BUNDLE_DELIVERY_INSTRUCTIONS = "bundle_delivery_instructions"
    BUNDLE_IDENTIFIER = "bundle_identifier"
    BUNDLE_INTENDED_DELIVERY_METHOD = "bundle_intended_delivery_method"
    BUNDLE_REQUIRED_DELIVERY_DATE = "bundle_required_delivery_date"
    BUNDLE_STATUS = "bundle_status"
    CONTRIBUTOR_REFERENCE = "contributor_reference"
    DELIVERED_BUNDLE_FILES = "delivered_bundle_files"
    DELIVERY_ATTEMPT_CONFIRMATION_FILES = "delivery_attempt_confirmation_files"
    DELIVERY_ATTEMPT_DATE = "delivery_attempt_date"
    DELIVERY_ATTEMPT_IDENTIFIER = "delivery_attempt_identifier"
    DELIVERY_ATTEMPT_METHOD = "delivery_attempt_method"
    DELIVERY_ATTEMPT_NOTES = "delivery_attempt_notes"
    DELIVERY_ATTEMPT_OUTCOME = "delivery_attempt_outcome"
    DOCUMENT_DESCRIPTION = "document_description"
    DOCUMENT_FILE = "document_file"
    DOCUMENT_IDENTIFIER = "document_identifier"
    DOCUMENT_TITLE = "document_title"
    DOCUMENT_TYPE = "document_type"
    ENGAGEMENT_END_DATE = "engagement_end_date"
    ENGAGEMENT_OUTCOME_SUMMARY = "engagement_outcome_summary"
    ENGAGEMENT_START_DATE = "engagement_start_date"
    ENGAGEMENT_STATUS = "engagement_status"
    ENGAGEMENT_STEPS_TAKEN = "engagement_steps_taken"
    ENGAGEMENT_TARGET_LENGTH = "engagement_target_length"
    ENGAGEMENT_TYPE = "engagement_type"
    INCLUDED_DOCUMENT_IDENTIFIER_SNAPSHOT = "included_document_identifier_snapshot"
    INCLUDED_DOCUMENT_TITLE_SNAPSHOT = "included_document_title_snapshot"
    OTHER_PARTICIPANT = "other_participant"
    PARTICIPANT_EMAIL_ADDRESS = "participant_email_address"
    PARTICIPANT_NOTES = "participant_notes"
    PARTICIPANT_PHONE_NUMBER = "participant_phone_number"
    PARTICIPANT_PORTAL_URL = "participant_portal_url"
    PARTICIPANT_ROLE = "participant_role"
    PARTICIPANT_TYPE = "participant_type"
    RECIPIENT_CONTRIBUTOR_REFERENCE = "recipient_contributor_reference"
    RECIPIENT_EMAIL_ADDRESS = "recipient_email_address"
    RECIPIENT_NAME_AS_PROVIDED = "recipient_name_as_provided"
    RECIPIENT_PHONE_NUMBER = "recipient_phone_number"
    RECIPIENT_PORTAL_URL = "recipient_portal_url"
    SHOULD_BE_DELIVERED = "should_be_delivered"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(ProjectEngagementAliases)


class ProjectEngagementGroupAliases(AbstractAliases):
    DELIVERY_ATTEMPT_INCLUDED_DOCUMENT = "delivery_attempt_included_document"
    DOCUMENT_DELIVERY_BUNDLE = "document_delivery_bundle"
    DOCUMENT_DELIVERY_BUNDLE_N1 = "document_delivery_bundle_n1"
    ENGAGEMENT_DETAILS = "engagement_details"
    ENGAGEMENT_DOCUMENT = "engagement_document"
    ENGAGEMENT_PARTICIPANT = "engagement_participant"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(ProjectEngagementGroupAliases)
