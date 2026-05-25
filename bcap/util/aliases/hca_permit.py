from bcap.util.bcap_aliases import AbstractAliases


class HCAPermitAliases(AbstractAliases):
    # Partial subset of the hca_permit graph: only the nodes the dashboard
    # reads. Extend as more of the graph gets consumed.
    PERMIT_NUMBER = "permit_number"
    PERMIT_HOLDER = "permit_holder"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(HCAPermitAliases)
