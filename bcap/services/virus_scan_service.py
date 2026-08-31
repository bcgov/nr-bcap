"""ClamAV virus scanning of uploaded files. Set CLAMAV_ENABLED=True and
CLAMAV_HOST (CLAMAV_PORT defaults to 3310).

ScanningStorage is where it happens: every file arches writes goes through the
default storage, whichever save path put it there.
"""

import logging

import clamd
from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)


class VirusScanService:
    """Scans uploaded files against clamd."""

    @staticmethod
    def scan(file):
        """Return a list of errors ([] if clean or scanning is disabled)."""
        if not settings.CLAMAV_ENABLED:
            logger.warning("CLAMAV_ENABLED is off; accepting file unscanned")
            return []

        try:
            scanner = clamd.ClamdNetworkSocket(
                host=settings.CLAMAV_HOST,
                port=int(settings.CLAMAV_PORT),
                timeout=120,
            )
            status, reason = scanner.instream(file)["stream"]
        except clamd.BufferTooLongError:
            # clamd refuses streams over StreamMaxLength (25M by default).
            logger.error("ClamAV rejected an oversized stream")
            return ["File is too large to virus scan"]
        except (clamd.ClamdError, OSError) as e:
            logger.error("ClamAV scan failed: %s", e)
            return ["Unable to virus scan file"]
        finally:
            file.seek(0)

        if status == "FOUND":
            logger.error("ClamAV found %s", reason)
            return [f"File failed virus scan: {reason}"]
        return []


class ScanningStorage(S3Boto3Storage):
    """Default storage that refuses to write a file ClamAV objects to."""

    def _save(self, name, content):
        if errors := VirusScanService.scan(content):
            raise SuspiciousFileOperation(f"{errors[0]}: {name}")
        return super()._save(name, content)
