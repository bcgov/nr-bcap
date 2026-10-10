import codecs
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from bcap.permissions.groups import Groups
from bcap.search.search_export import BCAPSearchResultsExporter
from bcap.views.search import export_results
from tests.views.helpers import AuthTestHelper

_BOM = codecs.BOM_UTF8.decode("utf-8")


@override_settings(SEARCH_EXPORT_IMMEDIATE_DOWNLOAD_THRESHOLD=10000)
class TestExportResultsRouting(SimpleTestCase):
    def test_immediate_shapefile_uses_bcap_exporter(self):
        request = RequestFactory().get(
            "/search/export_results", {"format": "shp", "total": "1"}
        )
        export_files = [{"name": "export.prj", "outputfile": object()}]
        with (
            patch.object(BCAPSearchResultsExporter, "__init__", return_value=None),
            patch.object(
                BCAPSearchResultsExporter,
                "export",
                return_value=(export_files, {}),
            ) as mock_export,
            patch(
                "bcap.views.search.zip_utils.zip_response",
                return_value=HttpResponse(b"zipdata", content_type="application/zip"),
            ) as mock_zip,
            patch("bcap.views.search.arches_export_results") as mock_arches,
        ):
            response = export_results.__wrapped__(request)

        self.assertEqual(response.status_code, 200)
        mock_export.assert_called_once_with("shp", False)
        mock_zip.assert_called_once_with(export_files, zip_file_name="bcap_export.zip")
        mock_arches.assert_not_called()

    def test_immediate_shapefile_without_files_includes_user_diagnostic(self):
        request = RequestFactory().get(
            "/search/export_results", {"format": "shp", "total": "0"}
        )
        with (
            patch.object(BCAPSearchResultsExporter, "__init__", return_value=None),
            patch.object(
                BCAPSearchResultsExporter,
                "export",
                return_value=([], {}),
            ),
            patch(
                "bcap.views.search.zip_utils.zip_response",
                return_value=HttpResponse(b"zipdata", content_type="application/zip"),
            ) as mock_zip,
        ):
            response = export_results.__wrapped__(request)

        self.assertEqual(response.status_code, 200)
        files_zipped = mock_zip.call_args.args[0]
        self.assertEqual(files_zipped[0]["name"], "error.txt")
        diagnostic = files_zipped[0]["outputfile"].getvalue()
        self.assertIn("no instances", diagnostic)
        self.assertIn("exportable geometry nodes", diagnostic)

    def test_asynchronous_shapefile_uses_bcap_task_with_shp_format(self):
        request = RequestFactory().get(
            "/search/export_results", {"format": "shp", "total": "10001"}
        )
        request.user = MagicMock(id=42)
        with (
            patch(
                "bcap.views.search.task_management.check_if_celery_available",
                return_value=True,
            ),
            patch(
                "bcap.views.search.bcap_tasks.export_search_results.apply_async"
            ) as mock_apply_async,
            patch("bcap.views.search.arches_export_results") as mock_arches,
        ):
            response = export_results.__wrapped__(request)

        self.assertEqual(response.status_code, 200)
        task_args = mock_apply_async.call_args.args[0]
        self.assertEqual(task_args[0], 42)
        self.assertEqual(task_args[2], "shp")
        mock_arches.assert_not_called()


@override_settings(
    ROOT_URLCONF="tests.test_urls",
    SEARCH_EXPORT_IMMEDIATE_DOWNLOAD_THRESHOLD=10000,
)
class TestExportResultsView(AuthTestHelper, TestCase):
    def setUp(self):
        super().setUp()
        group, _ = Group.objects.get_or_create(name=Groups.RESOURCE_EXPORTER)
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
