# The datatype factory searches arches-app dirs before core, so this subclass
# wins the (datatypes.py, FileListDataType) row. Subclass the arches_querysets
# version, not core's - it is the one the per-tile API needs.
from arches_querysets.datatypes.file import FileListDataType as BaseFileListDataType
from django.utils.translation import gettext as _

from bcap.services.virus_scan_service import VirusScanService


class FileListDataType(BaseFileListDataType):
    # Storage scans again on write, but that path raises and surfaces as a 400.
    def validate(
        self,
        value,
        row_number=None,
        source=None,
        node=None,
        nodeid=None,
        strict=False,
        path=None,
        request=None,
        **kwargs,
    ):
        errors = super().validate(
            value, row_number, source, node, nodeid, strict, path, request, **kwargs
        )
        # Nothing to scan if the file was already rejected on type, count or size.
        if errors or not request:
            return errors
        return [
            {"type": "ERROR", "title": _("Virus Scan Failed"), "message": message}
            for file in self._get_files_from_request(request, str(node.pk))
            for message in VirusScanService.scan(file.file)
        ]
