from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from bcap.tasks.tasks import export_search_results


class TestExportSearchResults(SimpleTestCase):
    def test_empty_shapefile_export_writes_user_diagnostic(self):
        exporter = MagicMock()
        exporter.export.return_value = ([], {})
        exporter.write_export_zipfile.return_value = "export-id"
        user = SimpleNamespace(first_name="", username="exporter")

        with (
            patch("bcap.tasks.tasks.create_user_task_record"),
            patch("bcap.tasks.tasks.User.objects.get", return_value=user),
            patch(
                "bcap.search.search_export.BCAPSearchResultsExporter",
                return_value=exporter,
            ),
            patch("bcap.tasks.tasks.models.SearchExportHistory.objects.get") as history,
            patch("bcap.tasks.tasks.return_message_context", return_value={}),
            patch("bcap.tasks.tasks.to_long", return_value="later"),
            patch("arches.app.models.system_settings.SystemSettings.update_from_db"),
        ):
            history.return_value.downloadfile = "export.zip"
            export_search_results.run(
                42,
                {"path": "/search/export_results", "format": ["shp"]},
                "shp",
                False,
            )

        files = exporter.write_export_zipfile.call_args.args[0]
        self.assertEqual([item["name"] for item in files], ["error.txt"])
        diagnostic = files[0]["outputfile"].getvalue()
        self.assertIn("no instances", diagnostic)
        self.assertIn("exportable geometry nodes", diagnostic)
