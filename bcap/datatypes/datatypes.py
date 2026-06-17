# The datatype factory resolves the geojson row (modulename=datatypes.py,
# classname=GeojsonFeatureCollectionDataType) by searching arches-app dirs
# before core, so this re-export shadows the core class with the
# arches_querysets per-tile version. arches_querysets never wires it up itself.
from arches_querysets.datatypes.geojson import GeojsonFeatureCollectionDataType  # noqa: F401
