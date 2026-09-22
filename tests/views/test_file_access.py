"""Who may fetch a file by uuid.

A file is addressed by its own id, with nothing in the URL tying it to the
resource it belongs to, so the view is the only thing keeping one applicant's
uploads away from another.
"""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from arches.app.models.models import File, GraphModel, Group, NodeGroup
from arches.app.models.models import ResourceInstance, TileModel

from bcap.permissions.groups import ANONYMOUS_USERNAME, Groups
from bcap.util.bcap_aliases import GraphSlugs
from bcap.views.file import BCAPFileView
from tests.builders import FixtureBuilder
from tests.controlled_list_fixtures import ControlledListFixtures
from tests.permit_fixtures import build_permit
from tests.services.contributor_fixtures import make_contributor, make_party
from tests.services.message_fixtures import make_message
from tests.views.helpers import login_as


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


class MessageAttachmentAccessTests(TestCase):
    """A message points at a permit rather than hanging off one, so no permit
    reaches it and its attachments answer to the thread's own visibility."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        builder = FixtureBuilder()
        acme = make_contributor(builder, "Acme Corp")
        cls.staff, staff_contrib = make_party(
            builder, "attach-staff", "Sam", "Staff", internal=True
        )
        cls.applicant, applicant_contrib = make_party(
            builder,
            "attach-applicant",
            "Amy",
            "Applicant",
            associated_organization=acme,
        )
        cls.outsider = make_party(builder, "attach-outsider", "Otto", "Outsider")[0]
        permit = build_permit(builder, "Attachment App", organization=acme)

        cls.public = make_message(
            builder,
            context=permit,
            author=staff_contrib,
            recipient=applicant_contrib,
            subject="Here is the form",
        )
        cls.internal = make_message(
            builder,
            context=permit,
            author=staff_contrib,
            recipient=staff_contrib,
            is_internal=True,
            subject="Between us",
        )

    def attachment(self, message):
        tile = TileModel.objects.filter(resourceinstance=message).first()
        return File.objects.create(tile=tile, path="uploadedfiles/note.txt").pk

    def test_who_reads_an_attachment(self):
        for name, expected, user, message in (
            ("a party on their own thread", True, self.applicant, self.public),
            ("an outsider to the thread", False, self.outsider, self.public),
            ("a party to an internal thread", False, self.applicant, self.internal),
        ):
            with self.subTest(name):
                fileid = self.attachment(message)
                readable = BCAPFileView.applicant_may_read(user, fileid)
                self.assertIs(bool(readable), expected)

    @override_settings(ROOT_URLCONF="tests.test_urls")
    def test_the_route_serves_a_reachable_attachment(self):
        """Arches checks the nodegroup after the view has checked the resource,
        so an applicant needs the seeded model-level grant to get this far. A
        redirect is the signed download."""
        login_as(self.client, self.applicant, "BCEID")
        url = reverse("files", kwargs={"fileid": self.attachment(self.public)})

        self.assertEqual(self.client.get(url).status_code, 302)

    @override_settings(ROOT_URLCONF="tests.test_urls")
    def test_the_route_refuses_the_public_user(self):
        """Arches' own check passes for it, since the stock groups carry the
        nodegroup grant, so the refusal has to come from the view."""
        login_as(self.client, User.objects.get(username=ANONYMOUS_USERNAME))
        url = reverse("files", kwargs={"fileid": self.attachment(self.public)})

        self.assertEqual(self.client.get(url).status_code, 403)

    @override_settings(ROOT_URLCONF="tests.test_urls")
    def test_the_route_serves_staff(self):
        login_as(self.client, self.staff)
        url = reverse("files", kwargs={"fileid": self.attachment(self.internal)})

        self.assertEqual(self.client.get(url).status_code, 302)
