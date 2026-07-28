# The arches_querysets serializer key wrapping each tile's node values.
ALIASED_DATA = "aliased_data"


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


class GraphSlugs:
    ALTERATION = "alteration"
    ARCHAEOLOGICAL_SITE = "archaeological_site"
    CONTRIBUTOR = "contributor"
    DOCUMENT_SUBMISSION = "document_submission"
    HCA_PERMIT = "hca_permit"
    HRIA_DISCONTINUED_DATA = "hria_discontinued_data"
    INSPECTION = "inspection"
    INVESTIGATION = "investigation"
    LEGISLATIVE_ACT = "legislative_act"
    PERMIT_APPLICATION = "permit_application"
    PROCESS_REQUIREMENT = "process_requirement"
    PUBLICATION = "publication"
    SITE_SUBMISSION = "site_submission"
    SITE_VISIT = "site_visit"
    WORKFLOW_DRAFTS = "workflow_drafts"
