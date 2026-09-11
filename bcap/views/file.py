"""File downloads, narrowed to the resource the file hangs off."""

from django.core.exceptions import PermissionDenied

from arches.app.models.models import File
from arches.app.utils.permission_backend import user_can_read_resource
from arches.app.views.file import FileView

from bcap.permissions.groups import is_internal_user
from bcap.services.message.bcap_message_service import BcapMessageService
from bcap.util.bcap_aliases import GraphSlugs


class BCAPFileView(FileView):
    """A file is addressed by uuid alone, and this view is what stands between
    an applicant and everyone else's uploads: storage is private, and the
    redirect it answers with is signed after the check.

    Which is why RESTRICT_MEDIA_ACCESS is off. That setting switches on arches'
    own check, and it asks whether the user may read the file's nodegroup: an
    answer that is the same for every applicant, skipped for search exports, and
    satisfied only by a permission nothing here grants, so leaving it on refused
    everyone. The question below covers the same files, plus exports and files
    on no tile, and the permission framework narrows the answer to the permits
    an applicant reaches.
    """

    def get(self, request, fileid=None):
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
            return BcapMessageService.base_query(
                user, resource_ids=[str(resource.pk)], as_representation=False
            ).exists()
        return user_can_read_resource(user, resource.pk)
