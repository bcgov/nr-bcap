from bcgov_arches_common.util.mvt_tiler_common import MVTTiler as MVTTiler_Base

from bcap.util.map_attributes import GRAPH_CONFIG


class MVTTiler(MVTTiler_Base):
    def __init__(self):
        pass

    query_cache = {}

    @staticmethod
    def get_query_config():
        # Format: NodeId : [ "field1", "field2", "field3" ]
        return {nodeid: attrs for nodeid, _, attrs in GRAPH_CONFIG.values()}
