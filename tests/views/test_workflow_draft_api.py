"""Tests for the generic per-user draft endpoints: a resource editor can POST a
draft, PATCH-merge sections into it, PUT-replace the whole blob, and DELETE it;
drafts are owner-scoped for external applicants (ministry staff see all), and the
graph publication is stamped on create so a stale draft can be detected. Drafts are stored as
resources of the 'drafts' graph (see WorkflowDraftService), not a bespoke table."""

import json
import uuid
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from arches.app.models.models import ResourceInstance

from bcap.services.workflow_draft_service import WorkflowDraftService
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import get_current_graph

from tests.views.helpers import AuthTestHelper

SLUG = GraphSlugs.PERMIT_APPLICATION


@override_settings(ROOT_URLCONF="tests.test_urls")
class WorkflowDraftApiTests(AuthTestHelper, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        User = get_user_model()
        cls.admin = User.objects.get(username="admin")
        editors = Group.objects.get(name="Resource Editor")
        cls.editor = User.objects.create_user(username="editor1", password="pass")
        cls.other_editor = User.objects.create_user(username="editor2", password="pass")
        cls.editor.groups.add(editors)
        cls.other_editor.groups.add(editors)
        # External applicants: unlike staff they only ever see their own drafts.
        submitters = Group.objects.get(name="Submitter")
        cls.applicant = User.objects.create_user(username="applicant1", password="pass")
        cls.other_applicant = User.objects.create_user(
            username="applicant2", password="pass"
        )
        cls.applicant.groups.add(submitters)
        cls.other_applicant.groups.add(submitters)
        # cls.user (from AuthTestHelper) intentionally holds neither role.

    def setUp(self):
        super().setUp()
        self.svc = WorkflowDraftService()
        self.idir_login_simulate(self.editor)
        self.list_url = reverse(
            "workflow_draft_list_create", kwargs={"graph_slug": SLUG}
        )

    def _detail_url(self, pk):
        return reverse("workflow_draft_detail", kwargs={"graph_slug": SLUG, "pk": pk})

    def _post(self, payload, url=None):
        return self.client.post(
            url or self.list_url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def _create_draft(self, user=None, data=None, publication_id=""):
        return self.svc.create(
            user or self.editor, SLUG, data or {}, publication_id=publication_id
        )

    def _read(self, pk):
        """The stored draft as a fresh record (bypasses the request layer)."""
        return self.svc.to_record(self.svc.get(self.admin, pk))

    def _make_resource(self, owner):
        """A bare resource of the draft's graph, owned by ``owner``."""
        resource = ResourceInstance.objects.create(graph_id=get_current_graph(SLUG).pk)
        ResourceInstance.objects.filter(pk=resource.pk).update(principaluser=owner)
        return resource

    def _draft_count(self):
        return ResourceInstance.objects.filter(
            graph__slug=GraphSlugs.WORKFLOW_DRAFTS
        ).count()

    def test_post_creates_draft_and_stamps_graph_publication(self):
        resp = self._post({"data": {"step1": {"x": 1}}, "frontend_version": "2.1.0"})
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["data"], {"step1": {"x": 1}})
        self.assertEqual(body["frontend_version"], "2.1.0")
        self.assertEqual(body["graph_slug"], SLUG)
        self.assertEqual(
            body["graph_publication_id"], str(get_current_graph(SLUG).publication_id)
        )
        self.assertEqual(
            ResourceInstance.objects.get(pk=body["id"]).principaluser, self.editor
        )

    def test_patch_merges_sections_then_put_replaces_blob(self):
        draft = self._create_draft(data={"step1": {"x": 1}})
        # PATCH merges, leaving siblings intact.
        resp = self.client.patch(
            self._detail_url(draft.id),
            data=json.dumps({"data": {"step2": {"y": 2}}}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            self._read(draft.id).data, {"step1": {"x": 1}, "step2": {"y": 2}}
        )
        # PUT replaces the whole blob.
        resp = self.client.put(
            self._detail_url(draft.id),
            data=json.dumps({"data": {"step3": {"z": 3}}}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._read(draft.id).data, {"step3": {"z": 3}})

    def test_patch_records_current_step_and_keeps_it_when_omitted(self):
        draft = self._create_draft(data={"step1": {"x": 1}})
        resp = self.client.patch(
            self._detail_url(draft.id),
            data=json.dumps({"data": {}, "current_step": "Contacts"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["current_step"], "Contacts")
        # A later save that doesn't mention the step leaves it where it was.
        self.client.patch(
            self._detail_url(draft.id),
            data=json.dumps({"data": {"step2": {"y": 2}}}),
            content_type="application/json",
        )
        self.assertEqual(self._read(draft.id).current_step, "Contacts")

    def test_create_stamps_descriptors(self):
        # A draft is referenced by other resources (a message's resource_context
        # points at it), and arches dereferences descriptors when building those
        # names. A null descriptor there is a 500, so create must stamp one.
        record = self._create_draft(data={"step1": {"x": 1}})
        resource = ResourceInstance.objects.get(pk=record.id)
        self.assertIsNotNone(resource.descriptors)

    def test_updated_is_stamped_on_create_and_bumped_on_save(self):
        t1 = datetime(2026, 7, 21, 10, 0, tzinfo=dt_timezone.utc)
        t2 = datetime(2026, 7, 21, 11, 30, tzinfo=dt_timezone.utc)
        with patch(
            "bcap.services.workflow_draft_service.timezone.now", return_value=t1
        ):
            resp = self._post({"data": {"step1": {"x": 1}}})
        self.assertEqual(resp.status_code, 201)
        draft_id = resp.json()["id"]
        self.assertIsNotNone(resp.json()["updated"])
        self.assertEqual(self._read(draft_id).updated, t1)

        # A later save advances the timestamp.
        with patch(
            "bcap.services.workflow_draft_service.timezone.now", return_value=t2
        ):
            resp = self.client.patch(
                self._detail_url(draft_id),
                data=json.dumps({"data": {"step2": {"y": 2}}}),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._read(draft_id).updated, t2)

    def test_applicant_list_is_owner_scoped_but_staff_see_all(self):
        self.idir_login_simulate(self.applicant)
        resp = self._post({"data": {"step1": {"x": 1}}})
        self.assertEqual(resp.status_code, 201)
        mine = resp.json()["id"]
        self._create_draft(user=self.other_applicant)
        # The applicant sees only their own draft; staff see both.
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual({row["id"] for row in resp.json()}, {mine})
        self.idir_login_simulate(self.editor)
        self.assertEqual(len(self.client.get(self.list_url).json()), 2)

    def test_non_owner_cannot_access_draft(self):
        self.idir_login_simulate(self.applicant)
        others = self._create_draft(user=self.other_applicant, data={"step1": {"x": 1}})
        url = self._detail_url(others.id)
        body = json.dumps({"data": {"step2": {"y": 2}}})
        for resp in (
            self.client.get(url),
            self.client.patch(url, data=body, content_type="application/json"),
            self.client.put(url, data=body, content_type="application/json"),
            self.client.delete(url),
        ):
            self.assertEqual(resp.status_code, 404)
        self.assertEqual(self._read(others.id).data, {"step1": {"x": 1}})  # untouched

    def test_graph_has_different_publication_flag(self):
        current = self._create_draft(
            publication_id=get_current_graph(SLUG).publication_id
        )
        stale = self._create_draft(publication_id=uuid.uuid4())
        self.assertFalse(
            self.client.get(self._detail_url(current.id)).json()[
                "graph_has_different_publication"
            ]
        )
        self.assertTrue(
            self.client.get(self._detail_url(stale.id)).json()[
                "graph_has_different_publication"
            ]
        )

    def test_delete_removes_draft(self):
        draft = self._create_draft()
        resp = self.client.delete(self._detail_url(draft.id))
        self.assertEqual(resp.status_code, 204)
        self.assertIsNone(self.svc.get(self.editor, draft.id))

    def test_post_with_owned_parent_resource_succeeds(self):
        parent = self._make_resource(self.editor)
        resp = self._post({"data": {}, "parent_resource_id": str(parent.pk)})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["parent_resource_id"], str(parent.pk))
        # Stored on its own node, never in the blob the client submits.
        self.assertEqual(self._read(resp.json()["id"]).data, {})

    def test_resource_editor_may_reference_another_users_resource(self):
        # A resource editor can edit any unrestricted resource, so the "or
        # resource editor" rule lets them link to one they don't own.
        parent = self._make_resource(self.other_editor)
        resp = self._post({"data": {}, "parent_resource_id": str(parent.pk)})
        self.assertEqual(resp.status_code, 201)

    def test_post_with_unknown_parent_resource_is_forbidden(self):
        before = self._draft_count()
        resp = self._post({"data": {}, "parent_resource_id": str(uuid.uuid4())})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(self._draft_count(), before)  # nothing saved

    def test_superuser_can_reference_any_parent_resource(self):
        parent = self._make_resource(self.other_editor)
        self.idir_login_simulate(self.admin)
        resp = self._post({"data": {}, "parent_resource_id": str(parent.pk)})
        self.assertEqual(resp.status_code, 201)

    def test_put_keeps_the_parent_resource(self):
        parent = self._make_resource(self.editor)
        draft_id = self._post(
            {"data": {}, "parent_resource_id": str(parent.pk)}
        ).json()["id"]
        resp = self.client.put(
            self._detail_url(draft_id),
            data=json.dumps({"data": {"step1": {"x": 1}}}),
            content_type="application/json",
        )
        self.assertEqual(resp.json()["parent_resource_id"], str(parent.pk))

    def test_internal_staff_can_read_any_applicants_draft(self):
        # Visibility is keyed on internal-group membership, not superuser: a
        # plain Resource Editor reaches an applicant's draft.
        draft = self._create_draft(user=self.applicant, data={"step1": {"x": 1}})
        self.assertFalse(self.editor.is_superuser)

        resp = self.client.get(self._detail_url(draft.id))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"], {"step1": {"x": 1}})

    def test_internal_staff_may_write_and_delete_an_applicants_draft(self):
        # Pins current behaviour: the internal-user widening applies to every
        # verb, so staff can overwrite and destroy an applicant's draft.
        draft = self._create_draft(user=self.applicant, data={"step1": {"x": 1}})
        resp = self.client.put(
            self._detail_url(draft.id),
            data=json.dumps({"data": {"step2": {"y": 2}}}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._read(draft.id).data, {"step2": {"y": 2}})

        self.assertEqual(
            self.client.delete(self._detail_url(draft.id)).status_code, 204
        )
        self.assertIsNone(self.svc.get(self.admin, draft.id))

    def test_an_applicant_cannot_read_another_applicants_draft(self):
        self.idir_login_simulate(self.applicant)
        others = self._create_draft(user=self.other_applicant)

        self.assertEqual(self.client.get(self._detail_url(others.id)).status_code, 404)

    def test_drafts_need_no_role_but_do_need_a_login(self):
        # Any signed-in user may keep drafts; owner scoping is what separates
        # them, not a role.
        self.idir_login_simulate(self.user)
        self.assertEqual(self._post({"data": {}}).status_code, 201)
        # Anonymous never reaches the view: auth middleware bounces it to login.
        self.client.logout()
        self.assertEqual(self._post({"data": {}}).status_code, 302)
        self.assertEqual(self.client.get(self.list_url).status_code, 302)
