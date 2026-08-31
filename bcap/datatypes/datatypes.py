# The datatype factory searches arches-app dirs before core, so this subclass
# wins the (datatypes.py, FileListDataType) row. Subclass the arches_querysets
# version, not core's - it is the one the per-tile API needs.
from arches_querysets.datatypes.file import FileListDataType as BaseFileListDataType

from bcap.services.virus_scan_service import VirusScanService


class FileListDataType(BaseFileListDataType):
    # Storage scans again on write, but that path raises and surfaces as a 400.
    # Scanning here puts the failure in the field's validation errors instead.
    def validate_file_types(self, request=None, nodeid=None):
        errors = super().validate_file_types(request, nodeid)
        for file in self._get_files_from_request(request, nodeid):
            errors = errors + VirusScanService.scan(file.file)
        return errors
