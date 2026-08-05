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

from arches.app.models.models import File

from bcap.builders.contributor_builder import ContributorSpec
from bcap.services.message.bcap_message_service import (
    MESSAGE_GRAPH_SLUG,
    ModuleUnread,
)
from bcap.services.workflow_draft_service import WorkflowDraftService
from bcap.util.controlled_list import reference_value
from tests.builders import FixtureBuilder
from tests.controlled_list_fixtures import ControlledListFixtures
from tests.services.test_bcap_message_service import make_message
from tests.views.helpers import AuthTestHelper


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
        cls.staff = get_user_model().objects.create_user(
            username="staff", password="pass"
        )
        cls.staff.groups.add(Group.objects.get(name="Resource Editor"))

        applicant_contrib = builder.make_contributor(
            ContributorSpec(
                contributor_type, "Amy", "Applicant", bcap_username="testuser"
            )
        )
        cls.applicant_contrib = applicant_contrib
        staff_contrib = builder.make_contributor(
            ContributorSpec(contributor_type, "Sam", "Staff", bcap_username="staff")
        )

        cls.permit = builder.make_resource("permit_application")
        cls.permit_id = str(cls.permit.pk)

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
        cls.internal_root = make_message(
            builder,
            context=cls.permit,
            author=staff_contrib,
            recipient=staff_contrib,
            is_internal=True,
            subject="Internal",
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

    def _post_message(self):
        payload = {
            "aliased_data": {
                "message_content": {
                    "aliased_data": {
                        "resource_context": {
                            "node_value": [{"resourceId": self.permit_id}]
                        },
                        "message_content": {
                            "node_value": {"en": {"value": "hi", "direction": "ltr"}}
                        },
                    }
                }
            }
        }
        return self.client.post(
            reverse("bcap_message_list_create"),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_create_denied_when_caller_cannot_edit_resource_context(self):
        # The create endpoint gates on edit access to the resource the message's
        # resource_context points at; when that check fails, the POST is refused
        # before any write.
        self.idir_login_simulate(self.user)
        with patch(
            "bcap.views.bcap_message_api.user_can_edit_resource", return_value=False
        ):
            resp = self._post_message()
        self.assertEqual(resp.status_code, 403)

    def test_create_allowed_when_caller_can_edit_resource_context(self):
        self.idir_login_simulate(self.user)
        with patch(
            "bcap.views.bcap_message_api.user_can_edit_resource", return_value=True
        ):
            resp = self._post_message()
        self.assertEqual(resp.status_code, 201)

    def test_create_against_a_draft_resource_context(self):
        draft = WorkflowDraftService().create(self.user, "investigation", {})
        payload = {
            "aliased_data": {
                "message_content": {
                    "aliased_data": {
                        "resource_context": {
                            "node_value": [{"resourceId": str(draft.pk)}]
                        },
                        "message_content": {
                            "node_value": {"en": {"value": "hi", "direction": "ltr"}}
                        },
                    }
                }
            }
        }
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
        with patch(
            "bcap.views.bcap_message_api.user_can_edit_resource", return_value=True
        ):
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
        payload = {
            "aliased_data": {
                "message_content": {
                    "aliased_data": {
                        "resource_context": {
                            "node_value": [{"resourceId": self.permit_id}]
                        },
                        "message_content": {
                            "node_value": {"en": {"value": "hi", "direction": "ltr"}}
                        },
                        "message_creation_date": {
                            "node_value": "2026-07-09T17:36:33.000Z"
                        },
                    }
                }
            }
        }
        self.idir_login_simulate(self.user)
        with patch(
            "bcap.views.bcap_message_api.user_can_edit_resource", return_value=True
        ):
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
        payload = {
            "aliased_data": {
                "message_content": {
                    "aliased_data": {
                        "resource_context": {
                            "node_value": [{"resourceId": self.permit_id}]
                        },
                        "message_content": {
                            "node_value": {"en": {"value": "hi", "direction": "ltr"}}
                        },
                        "attachments": {
                            "node_value": [{"name": "note.txt", "url": None}]
                        },
                    }
                }
            }
        }
        upload = SimpleUploadedFile(
            "note.txt", b"hello world", content_type="text/plain"
        )
        before = File.objects.count()
        self.idir_login_simulate(self.user)
        with patch(
            "bcap.views.bcap_message_api.user_can_edit_resource", return_value=True
        ):
            resp = self.client.post(
                reverse("bcap_message_list_create"),
                data={
                    "json": json.dumps(payload),
                    "attachments": upload,
                },
            )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(File.objects.count(), before + 1)

    def _patch_read_date(self, message_id, node_value):
        payload = {
            "aliased_data": {
                "message_content": {
                    "aliased_data": {
                        "message_read_date": {"node_value": node_value},
                    }
                }
            }
        }
        return self.client.patch(
            reverse("bcap_message_detail", kwargs={"pk": str(message_id)}),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def _patch_archived(self, message_id, archived):
        return self.client.patch(
            reverse("bcap_message_detail", kwargs={"pk": str(message_id)}),
            data=json.dumps({"archived": archived}),
            content_type="application/json",
        )

    def test_get_returns_the_message_when_caller_can_edit_context(self):
        # GET by id is gated like PATCH: edit access to the resource_context,
        # not owner-scoped, so staff (not the creator) can read it.
        self.idir_login_simulate(self.staff)
        with patch(
            "bcap.views.bcap_message_api.user_can_edit_resource", return_value=True
        ):
            resp = self.client.get(
                reverse("bcap_message_detail", kwargs={"pk": str(self.public_root.pk)})
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["resourceinstanceid"], str(self.public_root.pk))

    def test_get_denied_when_caller_cannot_edit_resource_context(self):
        self.idir_login_simulate(self.staff)
        with patch(
            "bcap.views.bcap_message_api.user_can_edit_resource", return_value=False
        ):
            resp = self.client.get(
                reverse("bcap_message_detail", kwargs={"pk": str(self.public_root.pk)})
            )
        self.assertEqual(resp.status_code, 403)

    def test_patch_marks_a_message_read(self):
        # Staff (the recipient, not the message's creator) marks it read.
        self.idir_login_simulate(self.staff)
        with patch(
            "bcap.views.bcap_message_api.user_can_edit_resource", return_value=True
        ):
            resp = self._patch_read_date(
                self.public_root.pk, "2026-07-10T14:04:46.334Z"
            )
        self.assertEqual(resp.status_code, 200)
        read = resp.json()["aliased_data"]["message_content"]["aliased_data"][
            "message_read_date"
        ]["node_value"]
        self.assertIsNotNone(read)

    def test_patch_can_mark_unread_by_clearing_the_date(self):
        self.idir_login_simulate(self.staff)
        with patch(
            "bcap.views.bcap_message_api.user_can_edit_resource", return_value=True
        ):
            self._patch_read_date(self.public_root.pk, "2026-07-10T14:04:46.334Z")
            resp = self._patch_read_date(self.public_root.pk, None)
        self.assertEqual(resp.status_code, 200)
        read = resp.json()["aliased_data"]["message_content"]["aliased_data"][
            "message_read_date"
        ]["node_value"]
        self.assertIsNone(read)

    def test_patch_denied_when_caller_cannot_edit_resource_context(self):
        # Same gate as create: no edit access to the resource_context, no write.
        self.idir_login_simulate(self.staff)
        with patch(
            "bcap.views.bcap_message_api.user_can_edit_resource", return_value=False
        ):
            resp = self._patch_read_date(
                self.public_root.pk, "2026-07-10T14:04:46.334Z"
            )
        self.assertEqual(resp.status_code, 403)

    def test_patch_ignores_writes_to_non_read_date_fields(self):
        # The endpoint is locked to the read state: a PATCH that also tries to
        # rewrite the message content changes only the read date, leaving the
        # content as it was.
        payload = {
            "aliased_data": {
                "message_content": {
                    "aliased_data": {
                        "message_read_date": {"node_value": "2026-07-10T14:04:46.334Z"},
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
        with patch(
            "bcap.views.bcap_message_api.user_can_edit_resource", return_value=True
        ):
            resp = self.client.patch(
                reverse("bcap_message_detail", kwargs={"pk": str(self.public_root.pk)}),
                data=json.dumps(payload),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 200)
        content = resp.json()["aliased_data"]["message_content"]["aliased_data"]
        self.assertIsNotNone(content["message_read_date"]["node_value"])
        # The seeded content ("Public") survived; the injected value did not.
        self.assertEqual(
            content["message_content"]["node_value"]["en"]["value"], "Public"
        )

    def test_patch_archives_thread_for_that_viewer_only(self):
        # A top-level "archived": true on the PATCH moves the thread to the
        # caller's archived list; the other party's view is untouched.
        self.idir_login_simulate(self.staff)
        with patch(
            "bcap.views.bcap_message_api.user_can_edit_resource", return_value=True
        ):
            resp = self._patch_archived(self.public_root.pk, True)
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
        with patch(
            "bcap.views.bcap_message_api.user_can_edit_resource", return_value=True
        ):
            self._patch_archived(self.public_root.pk, True)
            resp = self._patch_archived(self.public_root.pk, False)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(str(self.public_root.pk), self._thread_roots(self.staff))
        self.assertEqual(self._thread_roots(self.staff, archived=True), set())

    def test_patch_sets_read_date_and_archive_in_one_request(self):
        # The detail PATCH is shared: read date (a node in the body) and the
        # top-level archive flag both apply from a single request.
        payload = {
            "archived": True,
            "aliased_data": {
                "message_content": {
                    "aliased_data": {
                        "message_read_date": {"node_value": "2026-07-10T14:04:46.334Z"},
                    }
                }
            },
        }
        self.idir_login_simulate(self.staff)
        with patch(
            "bcap.views.bcap_message_api.user_can_edit_resource", return_value=True
        ):
            resp = self.client.patch(
                reverse("bcap_message_detail", kwargs={"pk": str(self.public_root.pk)}),
                data=json.dumps(payload),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 200)
        read = resp.json()["aliased_data"]["message_content"]["aliased_data"][
            "message_read_date"
        ]["node_value"]
        self.assertIsNotNone(read)
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
        with patch(
            "bcap.views.bcap_message_api.user_can_edit_resource", return_value=True
        ):
            resp = self._post_message()
        self.assertEqual(resp.status_code, 400)

    def test_module_unread_returns_the_serialized_counts(self):
        self.idir_login_simulate(self.user)
        url = reverse(
            "bcap_message_module_unread", kwargs={"submission_id": self.permit_id}
        )
        rows = [
            ModuleUnread(module_id="tile-1", unread_count=3),
            ModuleUnread(module_id="tile-2", unread_count=0),
        ]
        with patch(
            "bcap.views.bcap_message_api.BcapMessageService.unread_by_module",
            return_value=rows,
        ):
            resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            [
                {"module_id": "tile-1", "unread_count": 3},
                {"module_id": "tile-2", "unread_count": 0},
            ],
        )

    def test_module_unread_requires_authentication(self):
        url = reverse(
            "bcap_message_module_unread", kwargs={"submission_id": self.permit_id}
        )
        resp = self.client.get(url)
        # Unauthenticated is blocked: DRF denies (401/403), or the project's auth
        # middleware redirects to login (302). Any of these means "not served".
        self.assertIn(resp.status_code, (302, 401, 403))
