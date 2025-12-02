from bcap.util.bcap_aliases import AbstractAliases


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
