"""Virus scanning of uploads: clean files pass, infected files and an
unreachable scanner are rejected, no CLAMAV_HOST means no scanning, and the
storage backend refuses to write anything that fails a scan."""

from unittest import mock

import clamd
from arches.app.models.tile import TileValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
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
            self.assertIsNone(
                VirusScanService.scan(ContentFile(b"harmless", name="clean.txt"))
            )

    def test_infected_file_is_rejected(self):
        with fake_scanner(result=("FOUND", "Eicar-Test-Signature")):
            error = VirusScanService.scan(ContentFile(b"virus", name="bad.txt"))
        self.assertIn("Eicar-Test-Signature", error)

    def test_a_scan_error_is_not_treated_as_clean(self):
        # clamd reports a per-file failure as ERROR, not as a missing detection.
        with fake_scanner(result=("ERROR", "Can't allocate memory")):
            self.assertEqual(
                VirusScanService.scan(ContentFile(b"anything", name="any.txt")),
                "Unable to virus scan file",
            )

    def test_oversized_file_says_so(self):
        with fake_scanner(error=clamd.BufferTooLongError()):
            self.assertEqual(
                VirusScanService.scan(ContentFile(b"big", name="big.txt")),
                "File is too large to virus scan",
            )

    def test_unreachable_scanner_fails_closed(self):
        with fake_scanner(error=clamd.ConnectionError("no clamd")):
            self.assertEqual(
                VirusScanService.scan(ContentFile(b"anything", name="any.txt")),
                "Unable to virus scan file",
            )

    def test_an_already_read_file_is_still_scanned(self):
        # Thumbnailing and type checks read the file first, leaving it at EOF.
        file = ContentFile(b"virus", name="bad.txt")
        file.read()
        with fake_scanner(result=("FOUND", "Eicar-Test-Signature")) as scanner:
            error = VirusScanService.scan(file)
        self.assertIsNotNone(error)
        self.assertEqual(scanner.return_value.instream.call_args[0][0].tell(), 0)

    def test_file_is_rewound_for_the_next_reader(self):
        file = ContentFile(b"harmless", name="clean.txt")
        with fake_scanner(result=("OK", None)) as scanner:
            # clamd streams the file, so it is drained by the time we rewind it.
            scanner.return_value.instream.side_effect = lambda f: (
                f.read(),
                {"stream": ("OK", None)},
            )[1]
            VirusScanService.scan(file)
        self.assertEqual(file.read(), b"harmless")

    def test_scanning_is_off_when_disabled(self):
        with (
            override_settings(CLAMAV_ENABLED=False),
            fake_scanner(result=("FOUND", "nope")) as scanner,
        ):
            self.assertIsNone(
                VirusScanService.scan(ContentFile(b"virus", name="bad.txt"))
            )
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
                return (
                    ScanningStorage()._save(
                        "uploads/44/report-4804bdab-6725-4d0f-aa92-ea392851412e.pdf",
                        SimpleUploadedFile("report.pdf", b"x"),
                    ),
                    parent_save,
                )
            except TileValidationError as e:
                return e, parent_save

    def test_clean_file_is_written(self):
        saved, parent_save = self.save(("OK", None))
        self.assertEqual(saved, "saved")
        parent_save.assert_called_once()

    def test_infected_file_is_never_written(self):
        error, parent_save = self.save(("FOUND", "Eicar-Test-Signature"))
        self.assertIsInstance(error, TileValidationError)
        parent_save.assert_not_called()

    def test_the_error_names_the_file_as_the_caller_sent_it(self):
        # Not the stored path, and not the tile id the filename generator adds.
        error, _parent_save = self.save(("FOUND", "Eicar-Test-Signature"))
        self.assertIn("(report.pdf)", error.messages[0])
