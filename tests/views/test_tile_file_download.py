from types import SimpleNamespace
from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from arches.app.models.models import TileModel
from arches.app.views.tile import TileData

from bcap.services.records.audit import RecordsAuditService
from bcap.views.file import BCAPTileFileDownload


class TileFileDownloadTests(SimpleTestCase):
    def test_every_downloaded_file_is_audited(self):
        request = RequestFactory().get(
            "/tiles/download_files", {"tiles": '["t1"]', "node": "n1"}
        )
        request.user = SimpleNamespace(username="someone", pk=7)
        tile = SimpleNamespace(data={"n1": [{"file_id": "f1"}, {"file_id": "f2"}]})

        with (
            patch.object(TileData, "download_files", return_value=HttpResponse()),
            patch.object(TileModel.objects, "filter", return_value=[tile]),
            patch.object(RecordsAuditService, "log_read") as log_read,
        ):
            BCAPTileFileDownload().download_files(request)

        self.assertEqual([c.args[0] for c in log_read.call_args_list], ["f1", "f2"])
