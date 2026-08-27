"""ClamAV virus scanning of uploaded files.

Set CLAMAV_ENABLED=True and CLAMAV_HOST (CLAMAV_PORT defaults to 3310).

ScanningStorage is the backstop covering every upload boundary - arches writes
uploads through the default storage from the file datatype, /temp_file,
/images, the manifest manager and the ETL importers alike. The file datatype
also calls scan_file() directly so the common case reports a readable
validation error instead of a 400.
"""

import io
import logging

import clamd
from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)


def scan_file(file):
    """Return a list of errors ([] if clean or scanning is disabled)."""
    if not settings.CLAMAV_ENABLED:
        return []

    try:
        scanner = clamd.ClamdNetworkSocket(
            host=settings.CLAMAV_HOST,
            port=int(settings.CLAMAV_PORT),
            timeout=120,
        )
        contents = file.read()
        file.seek(0)
        status, reason = scanner.instream(io.BytesIO(contents))["stream"]
    except (clamd.ClamdError, OSError) as e:
        logger.error("ClamAV scan failed: %s", e)
        return ["Unable to virus scan file"]

    if status == "FOUND":
        logger.error("ClamAV found %s", reason)
        return [f"File failed virus scan: {reason}"]
    return []


class ScanningStorage(S3Boto3Storage):
    """Default storage that refuses to write a file ClamAV objects to."""

    def _save(self, name, content):
        if errors := scan_file(content):
            raise SuspiciousFileOperation(f"{errors[0]}: {name}")
        return super()._save(name, content)
