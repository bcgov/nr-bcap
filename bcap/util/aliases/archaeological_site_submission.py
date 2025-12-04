from bcap.util.bcap_aliases import AbstractAliases


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
