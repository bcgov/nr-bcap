from bcap.util.bcap_aliases import AbstractAliases


class HCAPermitAliases(AbstractAliases):
    HCA_PERMIT_TYPE = "hca_permit_type"
    ISSUING_AGENCY = "issuing_agency"
    PERMIT_HOLDER = "permit_holder"
    PERMIT_NUMBER = "permit_number"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(HCAPermitAliases)


class HCAPermitGroupAliases(AbstractAliases):
    PERMIT_IDENTIFICATION = "permit_identification"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(HCAPermitGroupAliases)
