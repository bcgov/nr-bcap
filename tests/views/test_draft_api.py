"""Tests for the generic per-user draft endpoints: a resource editor can POST a
draft, PATCH-merge sections into it, PUT-replace the whole blob, and DELETE it;
drafts are owner-scoped (superusers excepted), and the graph publication is
stamped on create so a stale draft can be detected. Drafts are stored as
resources of the 'drafts' graph (see DraftService), not a bespoke table."""

import json
import uuid
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from arches.app.models.models import ResourceInstance

from bcap.services.draft_service import DraftService
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import get_current_graph

from tests.views.helpers import AuthTestHelper

SLUG = GraphSlugs.PERMIT_APPLICATION


@override_settings(ROOT_URLCONF="tests.test_urls")
class ResourceDraftApiTests(AuthTestHelper, TestCase):
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
        # cls.user (from AuthTestHelper) is intentionally not a Resource Editor.

    def setUp(self):
        super().setUp()
        self.svc = DraftService()
        self.idir_login_simulate(self.editor)
        self.list_url = reverse(
            "resource_draft_list_create", kwargs={"graph_slug": SLUG}
        )

    def _detail_url(self, pk):
        return reverse("resource_draft_detail", kwargs={"graph_slug": SLUG, "pk": pk})

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
        return ResourceInstance.objects.filter(graph__slug=GraphSlugs.DRAFTS).count()

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

    def test_updated_is_stamped_on_create_and_bumped_on_save(self):
        t1 = datetime(2026, 7, 21, 10, 0, tzinfo=dt_timezone.utc)
        t2 = datetime(2026, 7, 21, 11, 30, tzinfo=dt_timezone.utc)
        with patch("bcap.services.draft_service.timezone.now", return_value=t1):
            resp = self._post({"data": {"step1": {"x": 1}}})
        self.assertEqual(resp.status_code, 201)
        draft_id = resp.json()["id"]
        self.assertIsNotNone(resp.json()["updated"])
        self.assertEqual(self._read(draft_id).updated, t1)

        # A later save advances the timestamp.
        with patch("bcap.services.draft_service.timezone.now", return_value=t2):
            resp = self.client.patch(
                self._detail_url(draft_id),
                data=json.dumps({"data": {"step2": {"y": 2}}}),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._read(draft_id).updated, t2)

    def test_list_is_owner_scoped_but_superuser_sees_all(self):
        mine = self._create_draft()
        self._create_draft(user=self.other_editor)
        # Editor sees only their own draft; superuser sees both.
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual({row["id"] for row in resp.json()}, {mine.id})
        self.idir_login_simulate(self.admin)
        self.assertEqual(len(self.client.get(self.list_url).json()), 2)

    def test_non_owner_cannot_access_draft(self):
        others = self._create_draft(user=self.other_editor, data={"step1": {"x": 1}})
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
        resp = self._post({"data": {"parent_resource_id": str(parent.pk)}})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["data"]["parent_resource_id"], str(parent.pk))

    def test_resource_editor_may_reference_another_users_resource(self):
        # A resource editor can edit any unrestricted resource, so the "or
        # resource editor" rule lets them link to one they don't own.
        parent = self._make_resource(self.other_editor)
        resp = self._post({"data": {"parent_resource_id": str(parent.pk)}})
        self.assertEqual(resp.status_code, 201)

    def test_post_with_unknown_parent_resource_is_forbidden(self):
        before = self._draft_count()
        resp = self._post({"data": {"parent_resource_id": str(uuid.uuid4())}})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(self._draft_count(), before)  # nothing saved

    def test_superuser_can_reference_any_parent_resource(self):
        parent = self._make_resource(self.other_editor)
        self.idir_login_simulate(self.admin)
        resp = self._post({"data": {"parent_resource_id": str(parent.pk)}})
        self.assertEqual(resp.status_code, 201)

    def test_patch_to_unknown_parent_resource_is_forbidden(self):
        draft = self._create_draft(data={"step1": {"x": 1}})
        resp = self.client.patch(
            self._detail_url(draft.id),
            data=json.dumps({"data": {"parent_resource_id": str(uuid.uuid4())}}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertNotIn("parent_resource_id", self._read(draft.id).data)  # untouched

    def test_without_resource_editor_role_is_forbidden(self):
        # Drafts are editor-only on every verb, reads included.
        self.idir_login_simulate(self.user)
        self.assertEqual(self._post({"data": {}}).status_code, 403)
        self.assertEqual(self.client.get(self.list_url).status_code, 403)
