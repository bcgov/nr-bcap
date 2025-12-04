from bcap.util.bcap_aliases import AbstractAliases


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

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(ContributorAliases)
