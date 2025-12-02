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
    ARCHAEOLOGICAL_SITE = "archaeological_site"
    HRIA_DISCONTINUED_DATA = "hria_discontinued_data"
    LEGISLATIVE_ACT = "legislative_act"
    SITE_SUBMISSION = "site_submission"
    SITE_VISIT = "site_visit"
