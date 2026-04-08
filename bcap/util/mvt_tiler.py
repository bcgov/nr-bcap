from bcgov_arches_common.util.mvt_tiler_common import MVTTiler as MVTTiler_Base


class MVTTiler(MVTTiler_Base):
    def __init__(self):
        pass

    query_cache = {}

    @staticmethod
    def get_query_config():
        return {
            "b18223c2-13ef-11f0-8695-0242ac170007": [
                "authorities",
                "borden_number",
                "registration_status",
            ],  # Archaeological Site
        }
