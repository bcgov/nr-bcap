# The datatype factory resolves the geojson row (modulename=datatypes.py,
# classname=GeojsonFeatureCollectionDataType) by searching arches-app dirs
# before core, so this re-export shadows the core class with the
# arches_querysets per-tile version. arches_querysets never wires it up itself.
from arches_querysets.datatypes.geojson import (
    GeojsonFeatureCollectionDataType,
)  # noqa: F401

# Same shadowing trick for file uploads, so every uploaded file gets virus
# scanned on top of the core type checks. Subclass the arches_querysets version,
# not core's - it is the one the per-tile API needs.
from arches_querysets.datatypes.file import FileListDataType as CoreFileListDataType

from bcap.services.virus_scan_service import VirusScanService


class FileListDataType(CoreFileListDataType):
    def validate_file_types(self, request=None, nodeid=None):
        errors = super().validate_file_types(request, nodeid)
        for file in self._get_files_from_request(request, nodeid):
            errors = errors + VirusScanService.scan(file.file)
        return errors
