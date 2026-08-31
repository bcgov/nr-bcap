"""ClamAV virus scanning of uploaded files. Set CLAMAV_ENABLED=True and
CLAMAV_HOST (CLAMAV_PORT defaults to 3310).

ScanningStorage is where it happens: every file arches writes goes through the
default storage, whichever save path put it there.
"""

import logging
import os
from typing import IO

import clamd
from arches.app.models.tile import TileValidationError
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)


class VirusScanService:
    """Scans uploaded files against clamd."""

    @staticmethod
    def scan(file: IO[bytes]) -> str | None:
        """Return why the file was refused, or None if it is clean."""
        if not settings.CLAMAV_ENABLED:
            logger.warning("CLAMAV_ENABLED is off; accepting file unscanned")
            return None

        file.seek(0)
        try:
            scanner = clamd.ClamdNetworkSocket(
                host=settings.CLAMAV_HOST,
                port=int(settings.CLAMAV_PORT),
                timeout=120,
            )
            status, reason = scanner.instream(file)["stream"]
        except clamd.BufferTooLongError:
            logger.error("ClamAV rejected an oversized stream")
            return "File is too large to virus scan"
        except (clamd.ClamdError, OSError) as e:
            logger.error("ClamAV scan failed: %s", e)
            return "Unable to virus scan file"
        finally:
            file.seek(0)

        if status == "FOUND":
            return f"File failed virus scan: {reason}"
        if status != "OK":
            logger.error("ClamAV returned %s: %s", status, reason)
            return "Unable to virus scan file"
        return None


class ScanningStorage(S3Boto3Storage):
    """Default storage that refuses to write a file ClamAV objects to."""

    def _save(self, name: str, content) -> str:
        if error := VirusScanService.scan(content):
            uploaded_name = content.name
            logger.error("Refused to store %s as %s: %s", uploaded_name, name, error)
            # TileValidationError Anything else leaves an empty resource behind, indexed.
            raise TileValidationError(f"{error} ({os.path.basename(uploaded_name)})")
        return super()._save(name, content)
