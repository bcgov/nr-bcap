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


class BCAPSiteSubmissionAliases(AbstractAliases):
    SUBMITTING_GOVERNMENT = "submitting_government"
    SUBMISSION_DATE = "submission_date"
    SUBMITTED_SITE_COUNT = "total_number_submitted"
    ARCHAEOLOGICAL_SITE = "archaeological_site"
    ASSIGNED_TO = "assigned_to"
    COMPLETION_DATE = "completion_date"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(BCAPSiteSubmissionAliases)


class BCAPLocalGovernmentAliases:
    TEST = "test"


class ContributorAliases(AbstractAliases):
    ASSOCIATED_ORGANIZATION = "associated_organization"
    ASSOCIATION_PERIOD = "association_period"
    CONTACT_EMAIL = "contact_email"
    CONTACT_INFORMATION = "contact_information"
    CONTACT_PHONE_NUMBER = "contact_phone_number"
    CONTRIBUTOR = "contributor"
    CONTRIBUTOR_NAME = "contributor_name"
    CONTRIBUTOR_ROLE = "contributor_role"
    CONTRIBUTOR_TYPE = "contributor_type"
    END_DATE = "end_date"
    FIRST_NAME = "first_name"
    INACTIVE = "inactive"
    NAME = "name"
    PALEOLOGICAL_CONSULTANT = "paleological_consultant"
    START_DATE = "start_date"


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
    ARCHAEOLOGICAL_SITE = "archaeological_site"
    HRIA_DISCONTINUED_DATA = "hria_discontinued_data"
    LEGISLATIVE_ACT = "legislative_act"
    SITE_SUBMISSION = "site_submission"
    SITE_VISIT = "site_visit"
