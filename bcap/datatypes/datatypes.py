# The datatype factory searches arches-app dirs before core, so this subclass
# wins the (datatypes.py, FileListDataType) row. Subclass the arches_querysets
# version, not core's - it is the one the per-tile API needs.
from arches_querysets.datatypes.file import FileListDataType as BaseFileListDataType

from bcap.services.virus_scan_service import VirusScanService


class FileListDataType(BaseFileListDataType):
    def validate_file_types(self, request=None, nodeid=None):
        errors = super().validate_file_types(request, nodeid)
        for file in self._get_files_from_request(request, nodeid):
            errors = errors + VirusScanService.scan(file.file)
        return errors
