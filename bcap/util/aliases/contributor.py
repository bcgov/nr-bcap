from bcap.util.bcap_aliases import AbstractAliases


class ContributorAliases(AbstractAliases):
    ADDRESS_LINE_1 = "address_line_1"
    ADDRESS_LINE_2 = "address_line_2"
    ASSOCIATED_ORGANIZATION = "associated_organization"
    BCAP_USERNAME = "bcap_username"
    CITY = "city"
    CONTACT_EMAIL = "contact_email"
    CONTACT_PHONE_NUMBER = "contact_phone_number"
    CONTRIBUTOR_DOCUMENT = "contributor_document"
    CONTRIBUTOR_DOCUMENT_TYPE = "contributor_document_type"
    CONTRIBUTOR_NAME = "contributor_name"
    CONTRIBUTOR_ROLE = "contributor_role"
    CONTRIBUTOR_TYPE = "contributor_type"
    END_DATE = "end_date"
    FIRST_NAME = "first_name"
    INACTIVE = "inactive"
    POSTAL_CODE = "postal_code"
    PROVINCE = "province"
    START_DATE = "start_date"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(ContributorAliases)


class ContributorGroupAliases(AbstractAliases):
    CONTRIBUTOR = "contributor"
    MAILING_ADDRESS = "mailing_address"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(ContributorGroupAliases)
