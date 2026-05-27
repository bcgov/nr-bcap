from bcap.util.bcap_aliases import AbstractAliases


class PublicationAliases(AbstractAliases):
    AGREEMENT_TEXT = "agreement_text"
    ARCHAEOLOGICAL_SITES = "archaeological_sites"
    AUTHORS = "authors"
    COPYRIGHT_TYPE = "copyright_type"
    DISTRIBUTION_PERMITTED = "distribution_permitted"
    INFORMATION_CARRIER = "information_carrier"
    JOURNAL_OR_VOLUME_NAME = "journal_or_volume_name"
    KEYWORD = "keyword"
    OTHER_AUTHORS_UNLISTED = "other_authors_unlisted"
    OTHER_JOURNAL_OR_VOLUME_NAME = "other_journal_or_volume_name"
    PAGE_RANGE_END = "page_range_end"
    PAGE_RANGE_START = "page_range_start"
    PUBLICATION_IDENTIFIER = "publication_identifier"
    PUBLICATION_IDENTIFIER_TYPE = "publication_identifier_type"
    PUBLICATION_REMARKS = "publication_remarks"
    PUBLICATION_TYPE = "publication_type"
    REPOSITORIES = "repositories"
    SIGNED_AGREEMENT = "signed_agreement"
    SITE_VISITS = "site_visits"
    TITLE = "title"
    YEAR_OF_PUBLICATION = "year_of_publication"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(PublicationAliases)
