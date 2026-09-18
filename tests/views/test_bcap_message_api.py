"""BCAP Message API endpoints end to end: the thread-roots and thread views
enforce the same internal/external visibility gate as the service, over a real
authenticated session; the create endpoint refuses a message whose
resource_context points at a resource the caller cannot edit."""

import json
from datetime import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from arches.app.models.models import File, ResourceInstance

from bcap.permissions.groups import Groups
from bcap.builders.contributor_builder import ContributorSpec
from bcap.services.message.bcap_message_service import ModuleUnresolved
from bcap.services.workflow_draft_service import WorkflowDraftService
from bcap.util.controlled_list import reference_value
from tests.builders import FixtureBuilder, request_as
from tests.controlled_list_fixtures import ControlledListFixtures
from tests.permit_fixtures import RequirementRow, build_permit, make_requirement
from tests.services.test_bcap_message_service import make_message, resolution
from tests.views.helpers import AuthTestHelper, api_reference_value


@override_settings(ROOT_URLCONF="tests.test_urls")
class BcapMessageApiTests(AuthTestHelper, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ControlledListFixtures.seed()
        builder = FixtureBuilder()
        contributor_type = reference_value("contributor", "contributor_type")

        # cls.user (from AuthTestHelper) is the external applicant; a second
        # user is ministry staff.
        cls.user.groups.add(Group.objects.get(name=Groups.SUBMITTER))
        cls.staff = get_user_model().objects.create_user(
            username="staff", password="pass"
        )
        cls.staff.groups.add(Group.objects.get(name=Groups.ARCHAEOLOGY_BRANCH))
        # A signed-in account in no group: the route gate refuses it outright.
        cls.viewer = get_user_model().objects.create_user(
            username="viewer", password="pass"
        )

        applicant_contrib = builder.make_contributor(
            ContributorSpec(
                contributor_type, "Amy", "Applicant", bcap_username="testuser"
            )
        )
        cls.applicant_contrib = applicant_contrib
        staff_contrib = builder.make_contributor(
            ContributorSpec(contributor_type, "Sam", "Staff", bcap_username="staff")
        )
        cls.recipient_id = str(staff_contrib.pk)
        builder.make_contributor(
            ContributorSpec(contributor_type, "Vic", "Viewer", bcap_username="viewer")
        )

        # The applicant's own permit and the requirement attached to it: what an
        # applicant reaches through, since they hold no grant on either graph.
        cls.requirement = make_requirement(builder, "Referral")
        cls.permit = build_permit(builder, "Mine", [RequirementRow(cls.requirement)])
        cls.permit_id = str(cls.permit.pk)
        cls.other_permit = build_permit(builder, "Someone Else's")
        ResourceInstance.objects.filter(pk=cls.permit.pk).update(principaluser=cls.user)
        ResourceInstance.objects.filter(pk=cls.other_permit.pk).update(
            principaluser=cls.staff
        )

        cls.public_root = make_message(
            builder,
            context=cls.permit,
            author=applicant_contrib,
            recipient=staff_contrib,
            subject="Public",
        )
        make_message(
            builder,
            context=cls.permit,
            author=staff_contrib,
            recipient=applicant_contrib,
            subject="Reply",
            root=cls.public_root,
        )
        cls.requirement_message = make_message(
            builder,
            context=cls.requirement,
            author=staff_contrib,
            recipient=applicant_contrib,
            subject="On the requirement",
        )
        cls.internal_root = make_message(
            builder,
            context=cls.permit,
            author=staff_contrib,
            recipient=staff_contrib,
            is_internal=True,
            subject="Internal",
        )
        cls.internal_requirement_root = make_message(
            builder,
            context=cls.requirement,
            author=staff_contrib,
            recipient=staff_contrib,
            is_internal=True,
            subject="Internal on the requirement",
        )
        cls.internal_requirement_reply = make_message(
            builder,
            context=cls.requirement,
            author=staff_contrib,
            recipient=staff_contrib,
            is_internal=True,
            subject="Internal reply",
            root=cls.internal_requirement_root,
        )

    def _thread_roots(self, user, archived=False):
        self.idir_login_simulate(user)
        url = reverse(
            "bcap_message_resource_threads", kwargs={"resource_id": self.permit_id}
        )
        resp = self.client.get(url, {"archived": "true"} if archived else {})
        self.assertEqual(resp.status_code, 200)
        return {r["resourceinstanceid"] for r in resp.json()["results"]}

    def test_staff_sees_both_threads_including_internal(self):
        ids = self._thread_roots(self.staff)
        self.assertEqual(ids, {str(self.public_root.pk), str(self.internal_root.pk)})

    def test_applicant_sees_only_the_thread_they_are_party_to(self):
        ids = self._thread_roots(self.user)
        self.assertEqual(ids, {str(self.public_root.pk)})

    def test_thread_messages_paginate_with_limit_offset(self):
        # Standard DRF limit/offset envelope: full count, one page of results,
        # and a link to the next page.
        self.idir_login_simulate(self.staff)
        url = reverse(
            "bcap_message_thread_messages",
            kwargs={"thread_id": str(self.public_root.pk)},
        )
        resp = self.client.get(url, {"limit": 1, "offset": 0})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["count"], 2)
        self.assertEqual(len(body["results"]), 1)
        self.assertIsNotNone(body["next"])

    def test_applicant_gets_empty_internal_thread(self):
        self.idir_login_simulate(self.user)
        url = reverse(
            "bcap_message_thread_messages",
            kwargs={"thread_id": str(self.internal_root.pk)},
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 0)

    def _message_payload(self, context_id=None, **extra_nodes):
        """A create body with the nodes the model requires; extra_nodes adds to
        or overrides the message_content group."""
        nodes = {
            "resource_context": {
                "node_value": [{"resourceId": context_id or self.permit_id}]
            },
            "message_content": {
                "node_value": {"en": {"value": "hi", "direction": "ltr"}}
            },
            "message_subject": {
                "node_value": {"en": {"value": "Subject", "direction": "ltr"}}
            },
            "message_type": {
                "node_value": api_reference_value("bcap_message", "message_type")
            },
            "recipient": {"node_value": [{"resourceId": self.recipient_id}]},
            **extra_nodes,
        }
        return {"aliased_data": {"message_content": {"aliased_data": nodes}}}

    def _post_message(self):
        payload = self._message_payload()
        return self.client.post(
            reverse("bcap_message_list_create"),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_create_denied_when_caller_cannot_edit_resource_context(self):
        # A caller with no reach into the resource the message's resource_context
        # points at is refused before any write.
        self.idir_login_simulate(self.viewer)
        resp = self._post_message()
        self.assertEqual(resp.status_code, 403)

    def test_create_allowed_on_the_applicants_own_permit(self):
        self.idir_login_simulate(self.user)
        resp = self._post_message()
        self.assertEqual(resp.status_code, 201)

    def test_applicant_creates_against_a_requirement_on_their_own_permit(self):
        # The applicant holds no grant on process_requirement, so the arches
        # edit check says no; reaching it through their own permit is what lets
        # the message through.
        self.idir_login_simulate(self.user)
        resp = self.client.post(
            reverse("bcap_message_list_create"),
            data=json.dumps(self._message_payload(str(self.requirement.pk))),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_applicant_cannot_start_an_internal_thread(self):
        self.idir_login_simulate(self.user)
        payload = self._message_payload(is_internal={"node_value": True})
        resp = self.client.post(
            reverse("bcap_message_list_create"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        content = resp.json()["aliased_data"]["message_content"]["aliased_data"]
        self.assertFalse(content["is_internal"]["node_value"])

    def test_applicant_cannot_reply_into_an_internal_thread(self):
        self.idir_login_simulate(self.user)
        payload = self._message_payload()
        payload["aliased_data"]["related_source_message"] = {
            "aliased_data": {
                "related_source_message": {
                    "node_value": [{"resourceId": str(self.internal_root.pk)}]
                }
            }
        }
        messages = ResourceInstance.objects.filter(graph__slug="bcap_message")
        before = messages.count()
        resp = self.client.post(
            reverse("bcap_message_list_create"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(messages.count(), before)

    def test_applicant_cannot_create_against_someone_elses_permit(self):
        self.idir_login_simulate(self.user)
        resp = self.client.post(
            reverse("bcap_message_list_create"),
            data=json.dumps(self._message_payload(str(self.other_permit.pk))),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_applicant_cannot_read_threads_on_someone_elses_permit(self):
        self.idir_login_simulate(self.user)
        resp = self.client.get(
            reverse(
                "bcap_message_resource_threads",
                kwargs={"resource_id": str(self.other_permit.pk)},
            )
        )
        self.assertEqual(resp.status_code, 403)

    def test_applicant_patches_a_message_filed_on_their_requirement(self):
        # The detail route runs the same gate: the applicant cannot edit a
        # process_requirement, but reaches this one through their permit.
        self.idir_login_simulate(self.user)
        resp = self._patch(self.requirement_message.pk, resolved=True)
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_applicant_reads_the_contributors_of_their_own_permit(self):
        self.idir_login_simulate(self.user)
        resp = self.client.get(
            reverse(
                "bcap_message_resource_contributors",
                kwargs={"resource_id": self.permit_id},
            )
        )
        self.assertEqual(resp.status_code, 200)

    def test_applicant_cannot_read_the_contributors_of_another_permit(self):
        self.idir_login_simulate(self.user)
        resp = self.client.get(
            reverse(
                "bcap_message_resource_contributors",
                kwargs={"resource_id": str(self.other_permit.pk)},
            )
        )
        self.assertEqual(resp.status_code, 403)

    def test_applicant_cannot_read_a_message_on_another_permit(self):
        # The message itself is not the gate: its resource_context is, so a
        # message filed on a permit the applicant cannot reach stays closed.
        other_message = make_message(
            FixtureBuilder(),
            context=self.other_permit,
            author=self.applicant_contrib,
            recipient=self.applicant_contrib,
            subject="Not yours",
        )
        self.idir_login_simulate(self.user)
        resp = self.client.get(
            reverse("bcap_message_detail", kwargs={"pk": str(other_message.pk)})
        )
        self.assertEqual(resp.status_code, 403)

    def test_staff_create_allowed_by_their_change_grant(self):
        self.idir_login_simulate(self.staff)
        resp = self._post_message()
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_staff_contributors_follow_their_read_access(self):
        url = reverse(
            "bcap_message_resource_contributors",
            kwargs={"resource_id": self.permit_id},
        )
        self.idir_login_simulate(self.staff)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_applicant_cannot_read_a_thread_on_another_permit(self):
        other_thread = make_message(
            FixtureBuilder(),
            context=self.other_permit,
            author=self.applicant_contrib,
            recipient=self.applicant_contrib,
            subject="Not yours",
        )
        self.idir_login_simulate(self.user)
        resp = self.client.get(
            reverse(
                "bcap_message_thread_messages",
                kwargs={"thread_id": str(other_thread.pk)},
            )
        )
        self.assertEqual(resp.status_code, 403)

    def test_applicant_cannot_read_unresolved_counts_of_another_submission(self):
        self.idir_login_simulate(self.user)
        resp = self.client.get(
            reverse(
                "bcap_message_module_unresolved",
                kwargs={"submission_id": str(self.other_permit.pk)},
            )
        )
        self.assertEqual(resp.status_code, 403)

    def test_applicant_reads_threads_on_a_requirement_of_their_permit(self):
        self.idir_login_simulate(self.user)
        resp = self.client.get(
            reverse(
                "bcap_message_resource_threads",
                kwargs={"resource_id": str(self.requirement.pk)},
            )
        )
        self.assertEqual(resp.status_code, 200)

    def test_create_against_a_draft_resource_context(self):
        draft = WorkflowDraftService().create(
            request_as(self.user), "investigation", {}
        )
        payload = self._message_payload(str(draft.pk))
        self.idir_login_simulate(self.user)
        resp = self.client.post(
            reverse("bcap_message_list_create"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_create_stamps_the_posting_user_as_author(self):
        # The poster's Contributor (resolved from their username) is written as
        # the message author, even though the payload never sets it.
        self.idir_login_simulate(self.user)
        resp = self._post_message()
        self.assertEqual(resp.status_code, 201)
        author = resp.json()["aliased_data"]["message_content"]["aliased_data"][
            "message_author"
        ]
        ids = [rel["resourceId"] for rel in (author["node_value"] or [])]
        self.assertEqual(ids, [str(self.applicant_contrib.pk)])

    def test_create_keeps_the_offset_bearing_creation_datetime(self):
        # A creation datetime with a UTC offset survives the write path: the
        # custom serializer field keeps the offset DRF would otherwise strip
        # under USE_TZ off, so the value passes validation and indexing (rather
        # than 400ing) and reads back as the same instant, time-of-day intact.
        payload = self._message_payload(
            message_creation_date={"node_value": "2026-07-09T17:36:33.000Z"}
        )
        self.idir_login_simulate(self.user)
        resp = self.client.post(
            reverse("bcap_message_list_create"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        stored = resp.json()["aliased_data"]["message_content"]["aliased_data"][
            "message_creation_date"
        ]["node_value"]
        # Kept its UTC offset and reads back as the same instant that was posted.
        # Arches returns it space-separated, which the generated Zod date schema
        # now accepts; fromisoformat parses either separator.
        self.assertEqual(
            datetime.fromisoformat(stored.replace(" ", "T")),
            datetime.fromisoformat("2026-07-09T17:36:33+00:00"),
        )

    def test_create_with_a_multipart_attachment_stores_the_file(self):
        # A message can carry a file: the collection endpoint accepts multipart
        # (a "json" part plus files under the "attachments" alias key), re-keys
        # them to the file-list node, and arches links the upload by name.
        payload = self._message_payload(
            attachments={"node_value": [{"name": "note.txt", "url": None}]}
        )
        upload = SimpleUploadedFile(
            "note.txt", b"hello world", content_type="text/plain"
        )
        before = File.objects.count()
        self.idir_login_simulate(self.user)
        resp = self.client.post(
            reverse("bcap_message_list_create"),
            data={
                "json": json.dumps(payload),
                "attachments": upload,
            },
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(File.objects.count(), before + 1)

    def test_patching_a_thread_keeps_its_attachments(self):
        # A PATCH writes the root; it must not re-save the attachments through
        # the file-list datatype, which deleted their stored files, so a second
        # open of an attachment 404'd.
        payload = self._message_payload(
            attachments={"node_value": [{"name": "keep.txt", "url": None}]}
        )
        self.idir_login_simulate(self.user)
        resp = self.client.post(
            reverse("bcap_message_list_create"),
            data={
                "json": json.dumps(payload),
                "attachments": SimpleUploadedFile("keep.txt", b"kept"),
            },
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        message_id = resp.json()["resourceinstanceid"]
        stored = File.objects.get(tile__resourceinstance_id=message_id)

        self.assertEqual(self._patch(message_id, resolved=True).status_code, 200)
        self.assertEqual(self._patch(message_id, resolved=False).status_code, 200)
        self.assertEqual(self._patch(message_id, archived=True).status_code, 200)
        self.assertEqual(self._patch(message_id, archived=False).status_code, 200)

        after = File.objects.get(tile__resourceinstance_id=message_id)
        self.assertEqual(after.pk, stored.pk)
        self.assertEqual(after.path.name, stored.path.name)
        self.assertTrue(after.path.storage.exists(after.path.name))

    def _patch(self, message_id, **body):
        return self.client.patch(
            reverse("bcap_message_detail", kwargs={"pk": str(message_id)}),
            data=json.dumps(body),
            content_type="application/json",
        )

    def _get_detail(self, message_id):
        return self.client.get(
            reverse("bcap_message_detail", kwargs={"pk": str(message_id)})
        )

    def test_get_returns_the_message_when_caller_can_read_context(self):
        # GET by id is gated on read access to the resource_context, not
        # owner-scoped, so staff (not the creator) can read it.
        self.idir_login_simulate(self.staff)
        resp = self._get_detail(self.public_root.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["resourceinstanceid"], str(self.public_root.pk))

    def test_applicant_cannot_read_an_internal_message_on_their_own_permit(self):
        # The thread listing hides it, so by-id is the way round the listing:
        # the context gate passes, since the permit is theirs.
        self.idir_login_simulate(self.user)
        self.assertEqual(self._get_detail(self.internal_root.pk).status_code, 404)

    def _requirement_threads(self):
        resp = self.client.get(
            reverse(
                "bcap_message_resource_threads",
                kwargs={"resource_id": str(self.requirement.pk)},
            )
        )
        self.assertEqual(resp.status_code, 200)
        return {r["resourceinstanceid"] for r in resp.json()["results"]}

    def _thread_count(self, thread_id):
        resp = self.client.get(
            reverse(
                "bcap_message_thread_messages", kwargs={"thread_id": str(thread_id)}
            )
        )
        self.assertEqual(resp.status_code, 200)
        return resp.json()["count"]

    def test_applicant_cannot_get_an_internal_thread_on_their_requirement(self):
        self.idir_login_simulate(self.user)
        self.assertNotIn(
            str(self.internal_requirement_root.pk), self._requirement_threads()
        )
        self.assertEqual(self._thread_count(self.internal_requirement_root.pk), 0)
        for message in (
            self.internal_requirement_root,
            self.internal_requirement_reply,
        ):
            self.assertEqual(self._get_detail(message.pk).status_code, 404)

    def test_staff_get_an_internal_thread_on_a_requirement(self):
        self.idir_login_simulate(self.staff)
        self.assertIn(
            str(self.internal_requirement_root.pk), self._requirement_threads()
        )
        self.assertEqual(self._thread_count(self.internal_requirement_root.pk), 2)
        for message in (
            self.internal_requirement_root,
            self.internal_requirement_reply,
        ):
            self.assertEqual(self._get_detail(message.pk).status_code, 200)

    def test_applicant_cannot_patch_an_internal_message_on_their_own_permit(self):
        self.idir_login_simulate(self.user)
        resp = self._patch(self.internal_root.pk, resolved=True)
        self.assertEqual(resp.status_code, 404)
        for side in ("author", "recipient"):
            self.assertEqual(resolution(self.internal_root, side), (None, None))

    # The applicant started the public thread, so staff are its recipient side.
    def test_staff_patch_resolves_their_side_only(self):
        self.idir_login_simulate(self.staff)
        resp = self._patch(self.public_root.pk, resolved=True)
        self.assertEqual(resp.status_code, 200)
        content = resp.json()["aliased_data"]["message_content"]["aliased_data"]
        self.assertIsNotNone(content["recipient_resolved_date"]["node_value"])
        resolved_by = content["recipient_resolved_by"]["node_value"]
        self.assertEqual(resolved_by[0]["resourceId"], self.recipient_id)
        self.assertIsNone(content["author_resolved_date"]["node_value"])

    def test_applicant_patch_resolves_their_side_only(self):
        self.idir_login_simulate(self.user)
        self.assertEqual(
            self._patch(self.public_root.pk, resolved=True).status_code, 200
        )
        self.assertEqual(
            resolution(self.public_root, "author")[1],
            str(self.applicant_contrib.pk),
        )
        self.assertEqual(resolution(self.public_root, "recipient"), (None, None))

    def test_threads_tell_the_viewer_their_side_and_whether_they_are_staff(self):
        for user, side, staff in (
            (self.staff, "recipient", True),
            (self.user, "author", False),
        ):
            self.idir_login_simulate(user)
            resp = self.client.get(
                reverse(
                    "bcap_message_resource_threads",
                    kwargs={"resource_id": self.permit_id},
                )
            )
            roots = {r["resourceinstanceid"]: r for r in resp.json()["results"]}
            root = roots[str(self.public_root.pk)]
            self.assertEqual(root["viewer_side"], side)
            self.assertIs(root["viewer_is_staff"], staff)

    def test_patch_reopens_the_thread(self):
        self.idir_login_simulate(self.staff)
        self._patch(self.public_root.pk, resolved=True)
        resp = self._patch(self.public_root.pk, resolved=False)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resolution(self.public_root, "recipient"), (None, None))

    def test_patch_denied_when_caller_cannot_edit_resource_context(self):
        # Same gate as create: no edit access to the resource_context, no write.
        self.idir_login_simulate(self.viewer)
        self.assertEqual(
            self._patch(self.public_root.pk, resolved=True).status_code, 403
        )

    def test_patch_ignores_node_edits(self):
        # Only the commands apply: a PATCH carrying a node value leaves the
        # message as it was.
        payload = {
            "aliased_data": {
                "message_content": {
                    "aliased_data": {
                        "message_content": {
                            "node_value": {
                                "en": {"value": "HACKED", "direction": "ltr"}
                            }
                        },
                    }
                }
            }
        }
        self.idir_login_simulate(self.staff)
        resp = self._patch(self.public_root.pk, **payload)
        self.assertEqual(resp.status_code, 200)
        content = resp.json()["aliased_data"]["message_content"]["aliased_data"]
        self.assertEqual(
            content["message_content"]["node_value"]["en"]["value"], "Public"
        )

    def test_a_reply_reopens_the_thread_for_the_other_side(self):
        self.idir_login_simulate(self.staff)
        self._patch(self.public_root.pk, resolved=True)
        self.idir_login_simulate(self.user)
        self._patch(self.public_root.pk, resolved=True)
        payload = self._message_payload()
        payload["aliased_data"]["related_source_message"] = {
            "aliased_data": {
                "related_source_message": {
                    "node_value": [{"resourceId": str(self.public_root.pk)}]
                }
            }
        }
        resp = self.client.post(
            reverse("bcap_message_list_create"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        # The applicant wrote: staff's side reopens, the applicant's is kept.
        self.assertEqual(resolution(self.public_root, "recipient"), (None, None))
        self.assertEqual(
            resolution(self.public_root, "author")[1], str(self.applicant_contrib.pk)
        )

    def test_patch_archives_thread_for_that_viewer_only(self):
        # A top-level "archived": true on the PATCH moves the thread to the
        # caller's archived list; the other party's view is untouched.
        self.idir_login_simulate(self.staff)
        resp = self._patch(self.public_root.pk, archived=True)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(str(self.public_root.pk), self._thread_roots(self.staff))
        self.assertIn(
            str(self.public_root.pk),
            self._thread_roots(self.staff, archived=True),
        )
        # The applicant, also party to the thread, still sees it as active.
        self.assertIn(str(self.public_root.pk), self._thread_roots(self.user))
        self.assertEqual(self._thread_roots(self.user, archived=True), set())

    def test_patch_unarchives_thread_back_to_active(self):
        self.idir_login_simulate(self.staff)
        self._patch(self.public_root.pk, archived=True)
        resp = self._patch(self.public_root.pk, archived=False)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(str(self.public_root.pk), self._thread_roots(self.staff))
        self.assertEqual(self._thread_roots(self.staff, archived=True), set())

    def test_patch_resolves_and_archives_in_one_request(self):
        self.idir_login_simulate(self.staff)
        resp = self._patch(self.public_root.pk, resolved=True, archived=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resolution(self.public_root, "recipient")[0])
        self.assertIn(
            str(self.public_root.pk),
            self._thread_roots(self.staff, archived=True),
        )

    def test_create_rejected_when_poster_has_no_contributor(self):
        # A user with no linked Contributor cannot author a message, so the
        # create is refused before any write.
        no_contrib = get_user_model().objects.create_user(
            username="stranger", password="pass"
        )
        self.idir_login_simulate(no_contrib)
        resp = self._post_message()
        self.assertEqual(resp.status_code, 400)

    def test_module_unresolved_returns_the_serialized_counts(self):
        self.idir_login_simulate(self.user)
        url = reverse(
            "bcap_message_module_unresolved", kwargs={"submission_id": self.permit_id}
        )
        rows = [
            ModuleUnresolved(module_id="tile-1", unresolved_count=3),
            ModuleUnresolved(module_id="tile-2", unresolved_count=0),
        ]
        with patch(
            "bcap.views.bcap_message_api.BcapMessageService.unresolved_by_module",
            return_value=rows,
        ):
            resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            [
                {"module_id": "tile-1", "unresolved_count": 3},
                {"module_id": "tile-2", "unresolved_count": 0},
            ],
        )

    def test_module_unresolved_requires_authentication(self):
        url = reverse(
            "bcap_message_module_unresolved", kwargs={"submission_id": self.permit_id}
        )
        resp = self.client.get(url)
        # Unauthenticated is blocked: DRF denies (401/403), or the project's auth
        # middleware redirects to login (302). Any of these means "not served".
        self.assertIn(resp.status_code, (302, 401, 403))
