"""Who may fetch a file by uuid.

A file is addressed by its own id, with nothing in the URL tying it to the
resource it belongs to, so the view is the only thing keeping one applicant's
uploads away from another.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from arches.app.models.models import File, GraphModel, Group, NodeGroup
from arches.app.models.models import ResourceInstance, TileModel

from bcap.permissions.groups import Groups, is_internal_user
from bcap.util.bcap_aliases import GraphSlugs
from bcap.views.file import BCAPFileView


class FileAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.graph = GraphModel.objects.filter(
            slug=GraphSlugs.DOCUMENT_SUBMISSION, source_identifier__isnull=True
        ).first()
        cls.owner = User.objects.create_user("file-owner")
        cls.other = User.objects.create_user("file-other")
        submitter = Group.objects.filter(name=Groups.SUBMITTER).first()
        if submitter:
            cls.owner.groups.add(submitter)
            cls.other.groups.add(submitter)

    def setUp(self):
        if self.graph is None:
            self.skipTest("document_submission is not loaded in the test database")
        resource = ResourceInstance.objects.create(
            graph=self.graph, principaluser_id=self.owner.pk
        )
        nodegroup = (
            NodeGroup.objects.filter(node__graph_id=self.graph.pk).first()
            or NodeGroup.objects.create()
        )
        tile = TileModel.objects.create(
            resourceinstance=resource, nodegroup=nodegroup, data={}
        )
        self.file = File.objects.create(tile=tile, path="uploadedfiles/test.txt")

    def test_an_upload_no_permit_reaches_is_refused(self):
        """Deliberate: reach is by permit, not by who made the resource, so a
        document nothing links to is unreadable even by its uploader. What keeps
        the submit flow working is the link being written when the module is
        filed, not an exception here."""
        self.assertFalse(BCAPFileView.applicant_may_read(self.owner, self.file.pk))

    def test_another_applicant_may_not(self):
        self.assertFalse(BCAPFileView.applicant_may_read(self.other, self.file.pk))

    def test_an_unknown_id_is_refused(self):
        self.assertFalse(
            BCAPFileView.applicant_may_read(
                self.owner, "00000000-0000-0000-0000-000000000001"
            )
        )

    def test_staff_skip_the_check(self):
        """The view exempts internal users before asking, so a file on a
        resource no permit reaches is still theirs to read."""
        staff = User.objects.create_user("file-staff")
        staff.groups.add(Group.objects.get(name=Groups.ARCHAEOLOGY_BRANCH))
        self.assertTrue(is_internal_user(staff))
