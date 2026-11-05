from unittest import mock

from django.core.files.base import ContentFile
from django.test import SimpleTestCase, override_settings
from storages.backends.s3boto3 import S3Boto3Storage

from bcap.services.records.classification import RecordTags, Sensitivity, Status
from bcap.services.records.storage import RecordsStorage


@override_settings(CLAMAV_ENABLED=False)
class RecordsStorageTests(SimpleTestCase):
    def setUp(self):
        self.storage = RecordsStorage(bucket_name="bcap")

    def write_parameters(self, name, tags=None):
        """The write parameters a save would send, without touching S3."""
        content = ContentFile(b"x", name="x.pdf")
        if tags:
            content.records_tags = tags
        written = {}

        def fake_save(storage, key, content):
            written.update(storage._get_write_parameters(key, content))
            return key

        with (
            mock.patch.object(
                S3Boto3Storage, "_save", autospec=True, side_effect=fake_save
            ),
            mock.patch.object(
                S3Boto3Storage,
                "get_available_name",
                side_effect=lambda n, max_length=None: n,
            ),
        ):
            self.storage.save(name, content)
        return written

    def test_scratch_paths(self):
        self.assertTrue(RecordsStorage.is_scratch("archestemp/a.pdf"))
        self.assertTrue(RecordsStorage.is_scratch("uploadedfiles/tmp/load/a.xlsx"))
        self.assertFalse(RecordsStorage.is_scratch("uploadedfiles/a.pdf"))
        self.assertFalse(RecordsStorage.is_scratch("archaeological_site/a-tile.pdf"))

    def test_upload_carries_its_tags(self):
        params = self.write_parameters(
            "archaeological_site/a-tile.pdf",
            RecordTags(
                orcs_classification="11300-35",
                sensitivity_class=Sensitivity.GENERAL,
                classification_status=Status.AUTO,
            ),
        )
        self.assertIn("orcs-classification=11300-35", params["Tagging"])
        self.assertIn("sensitivity-class=general", params["Tagging"])

    def test_record_without_tags_fails_closed(self):
        params = self.write_parameters("uploadedfiles/a.pdf")
        self.assertIn("sensitivity-class=site-location", params["Tagging"])
        self.assertIn("classification-status=unclassified", params["Tagging"])

    def test_scratch_files_are_not_tagged(self):
        params = self.write_parameters("archestemp/a.pdf")
        self.assertNotIn("Tagging", params)

    def test_record_delete_is_suppressed(self):
        with mock.patch.object(S3Boto3Storage, "delete") as delete:
            self.storage.delete("archaeological_site/a.pdf")
        delete.assert_not_called()

    def test_scratch_delete_goes_through(self):
        with mock.patch.object(S3Boto3Storage, "delete") as delete:
            self.storage.delete("archestemp/a.pdf")
        delete.assert_called_once_with("archestemp/a.pdf")
