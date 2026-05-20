import codecs
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from bcap.search.search_export import BCAPSearchResultsExporter
from tests.views.helpers import AuthTestHelper

_BOM = codecs.BOM_UTF8.decode("utf-8")


@override_settings(
    ROOT_URLCONF="tests.test_urls",
    SEARCH_EXPORT_IMMEDIATE_DOWNLOAD_THRESHOLD=10000,
)
class TestExportResultsView(AuthTestHelper, TestCase):
    def setUp(self):
        super().setUp()
        group, _ = Group.objects.get_or_create(name="Resource Exporter")
        self.user.groups.add(group)
        self.idir_login_simulate()
        self.url = reverse("export_results")

    def test_tilecsv_contains_bom(self):
        def fake_export(self_exporter, _format, _report_link):
            return ([self_exporter.to_csv([], [], "export")], {})

        with (
            patch.object(
                BCAPSearchResultsExporter,
                "__init__",
                lambda _self, search_request=None: None,
            ),
            patch.object(BCAPSearchResultsExporter, "export", fake_export),
            patch(
                "bcap.views.search.zip_utils.zip_response",
                return_value=HttpResponse(b"zipdata", content_type="application/zip"),
            ) as mock_zip,
        ):
            response = self.client.get(self.url, {"format": "tilecsv", "total": "1"})

        self.assertEqual(response.status_code, 200)
        files_zipped = mock_zip.call_args[0][0]
        self.assertTrue(files_zipped[0]["outputfile"].getvalue().startswith(_BOM))

    def test_non_tilecsv_falls_through_to_arches(self):
        with patch(
            "bcap.views.search.arches_export_results",
            return_value=HttpResponse(b"arches response"),
        ) as mock_arches:
            response = self.client.get(self.url, {"format": "geojson", "total": "1"})

        mock_arches.assert_called_once()
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_is_denied(self):
        self.client.logout()
        response = self.client.get(self.url, {"format": "tilecsv", "total": "1"})
        self.assertIn(response.status_code, [302, 403])
