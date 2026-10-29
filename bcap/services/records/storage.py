"""Default file storage: tags each upload with its ORCS classification and
never deletes a record. The filename generator leaves the tags on the file
being saved; Object Lock and versioning are bucket settings.
"""

import logging
from urllib.parse import urlencode

from django.conf import settings

from arches.app.models.models import SearchExportHistory, TempFile

from bcap.services.records.classification import RecordTags
from bcap.services.virus_scan_service import ScanningStorage

logger = logging.getLogger(__name__)

SCRATCH_PREFIXES = (
    f"{TempFile._meta.get_field('path').upload_to}/",
    f"{SearchExportHistory._meta.get_field('downloadfile').upload_to}/",
    f"{settings.UPLOADED_FILES_DIR}/tmp/",
)


class RecordsStorage(ScanningStorage):
    @staticmethod
    def is_scratch(name):
        return (name or "").startswith(SCRATCH_PREFIXES)

    def _get_write_parameters(self, name, content=None):
        params = super()._get_write_parameters(name, content)
        if not self.is_scratch(name):
            # Untagged means saved without the filename generator: a bulk import,
            # a direct storage write, or a save with no tile. The default tags
            # fail closed: restricted and unclassified until it's classified.
            tags = getattr(content, "records_tags", None) or RecordTags()
            params["Tagging"] = urlencode(tags.as_s3())
        return params

    def delete(self, name):
        if self.is_scratch(name):
            super().delete(name)
        else:
            # Records are only destroyed through disposition, never by Arches.
            logger.warning("Delete suppressed for record %s", name)
