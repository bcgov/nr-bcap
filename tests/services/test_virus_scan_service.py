"""Virus scanning of uploads: clean files pass, infected files and an
unreachable scanner are rejected, no CLAMAV_HOST means no scanning, and the
storage backend refuses to write anything that fails a scan."""

import io
from unittest import mock

import clamd
from django.core.exceptions import SuspiciousFileOperation
from django.test import SimpleTestCase, override_settings
from storages.backends.s3boto3 import S3Boto3Storage

from bcap.services.virus_scan_service import ScanningStorage, VirusScanService


def fake_scanner(result=None, error=None):
    scanner = mock.Mock()
    scanner.instream.side_effect = error
    if error is None:
        scanner.instream.return_value = {"stream": result}
    return mock.patch("clamd.ClamdNetworkSocket", return_value=scanner)


@override_settings(CLAMAV_ENABLED=True, CLAMAV_HOST="clamav", CLAMAV_PORT=3310)
class ClamAVScanTests(SimpleTestCase):
    def test_clean_file_passes(self):
        with fake_scanner(result=("OK", None)):
            self.assertEqual(VirusScanService.scan(io.BytesIO(b"harmless")), [])

    def test_infected_file_is_rejected(self):
        with fake_scanner(result=("FOUND", "Eicar-Test-Signature")):
            errors = VirusScanService.scan(io.BytesIO(b"virus"))
        self.assertEqual(len(errors), 1)
        self.assertIn("Eicar-Test-Signature", errors[0])

    def test_unreachable_scanner_fails_closed(self):
        with fake_scanner(error=clamd.ConnectionError("no clamd")):
            self.assertEqual(
                VirusScanService.scan(io.BytesIO(b"anything")),
                ["Unable to virus scan file"],
            )

    def test_file_is_rewound_for_the_next_reader(self):
        file = io.BytesIO(b"harmless")
        with fake_scanner(result=("OK", None)):
            VirusScanService.scan(file)
        self.assertEqual(file.read(), b"harmless")

    def test_scanning_is_off_when_disabled(self):
        with (
            override_settings(CLAMAV_ENABLED=False),
            fake_scanner(result=("FOUND", "nope")) as scanner,
        ):
            self.assertEqual(VirusScanService.scan(io.BytesIO(b"virus")), [])
            scanner.assert_not_called()


@override_settings(CLAMAV_ENABLED=True, CLAMAV_HOST="clamav", CLAMAV_PORT=3310)
class ScanningStorageTests(SimpleTestCase):
    def save(self, result):
        with (
            fake_scanner(result=result),
            mock.patch.object(
                S3Boto3Storage, "_save", return_value="saved"
            ) as parent_save,
        ):
            try:
                return ScanningStorage()._save("f.txt", io.BytesIO(b"x")), parent_save
            except SuspiciousFileOperation as e:
                return e, parent_save

    def test_clean_file_is_written(self):
        saved, parent_save = self.save(("OK", None))
        self.assertEqual(saved, "saved")
        parent_save.assert_called_once()

    def test_infected_file_is_never_written(self):
        error, parent_save = self.save(("FOUND", "Eicar-Test-Signature"))
        self.assertIsInstance(error, SuspiciousFileOperation)
        parent_save.assert_not_called()
