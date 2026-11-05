"""File downloads, narrowed to the resource the file hangs off."""

import json

from django.core.exceptions import PermissionDenied

from arches.app.models.models import File, TileModel
from arches.app.utils.permission_backend import user_can_read_resource
from arches.app.views.file import FileView
from arches.app.views.tile import TileData

from bcap.permissions.groups import is_anonymous_user, is_internal_user
from bcap.services.message.message_context import MessageViewer
from bcap.services.message.thread_service import ThreadService
from bcap.services.records.audit import RecordsAuditService
from bcap.util.bcap_aliases import GraphSlugs


class BCAPFileView(FileView):
    """A file is addressed by uuid alone, and this view is what stands between
    an applicant and everyone else's uploads: storage is private, and the
    redirect it answers with is signed after the check.

    Arches asks its own question afterwards, and the two are not the same one.
    Its question is whether the user may read the file's nodegroup, which is
    answered the same way for every applicant, skipped for search exports, and
    refused outright where a file hangs off no tile. The question below is the
    narrowing one: it covers exports and tile-less files too, and the permission
    framework answers it per resource, so an applicant reaches the uploads on
    their own permits and no one else's.
    """

    def get(self, request, fileid=None):
        try:
            response = self.checked_get(request, fileid)
        except PermissionDenied:
            self.log_read(request, fileid, 403)
            raise
        self.log_read(request, fileid, response.status_code)
        return response

    @staticmethod
    def log_read(request, fileid, status):
        RecordsAuditService.log_read(
            fileid,
            request.user,
            status,
            thumbnail=request.GET.get("thumbnail", "false") != "false",
        )

    def checked_get(self, request, fileid):
        if is_anonymous_user(request.user):
            raise PermissionDenied
        if not is_internal_user(request.user) and not self.applicant_may_read(
            request.user, fileid
        ):
            raise PermissionDenied
        return super().get(request, fileid)

    @staticmethod
    def applicant_may_read(user, fileid):
        file = (
            File.objects.filter(pk=fileid)
            .select_related("tile__resourceinstance__graph")
            .first()
        )
        if not (file and file.tile_id):
            return False
        resource = file.tile.resourceinstance
        # A message points at the permit rather than hanging off it, so no permit
        # reaches one and the reach check always says no. Its attachments follow
        # the thread's own rule instead: party to it, and not internal-only.
        if resource.graph.slug == GraphSlugs.BCAP_MESSAGE:
            return ThreadService.base_query(
                MessageViewer.for_user(user),
                resource_ids=[str(resource.pk)],
                as_representation=False,
            ).exists()
        return user_can_read_resource(user, resource.pk)


class BCAPTileFileDownload(TileData):
    """The file viewer's download: one file redirects straight to storage and
    several are zipped, so neither passes through the file view's audit."""

    def download_files(self, request):
        response = super().download_files(request)
        nodeid = request.GET.get("node")
        tiles = TileModel.objects.filter(
            pk__in=json.loads(request.GET.get("tiles") or "[]")
        )
        for tile in tiles:
            for entry in (tile.data or {}).get(nodeid) or []:
                RecordsAuditService.log_read(
                    entry["file_id"],
                    request.user,
                    response.status_code,
                    thumbnail=False,
                )
        return response
