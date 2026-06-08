"""Tests for the generic per-user draft endpoints: a resource editor can POST a
draft, PATCH-merge sections into it, PUT-replace the whole blob, and DELETE it;
drafts are owner-scoped (superusers excepted), and the graph publication is
stamped on create so a stale draft can be detected."""

import json
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from bcap.models.resource_draft import ResourceDraft
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

    def _create_draft(self, **fields):
        return ResourceDraft.objects.create(user=self.editor, graph_slug=SLUG, **fields)

    def test_post_creates_draft_and_stamps_graph_publication(self):
        resp = self._post({"data": {"step1": {"x": 1}}, "frontend_version": "2.1.0"})
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["data"], {"step1": {"x": 1}})
        self.assertEqual(body["frontend_version"], "2.1.0")
        self.assertEqual(body["graph_slug"], SLUG)

        draft = ResourceDraft.objects.get(draftid=body["draftid"])
        self.assertEqual(draft.user, self.editor)
        self.assertEqual(
            draft.graph_publication_id, get_current_graph(SLUG).publication_id
        )

    def test_patch_merges_sections_then_put_replaces_blob(self):
        draft = self._create_draft(data={"step1": {"x": 1}})
        # PATCH merges, leaving siblings intact.
        resp = self.client.patch(
            self._detail_url(draft.pk),
            data=json.dumps({"data": {"step2": {"y": 2}}}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        draft.refresh_from_db()
        self.assertEqual(draft.data, {"step1": {"x": 1}, "step2": {"y": 2}})
        # PUT replaces the whole blob.
        resp = self.client.put(
            self._detail_url(draft.pk),
            data=json.dumps({"data": {"step3": {"z": 3}}}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        draft.refresh_from_db()
        self.assertEqual(draft.data, {"step3": {"z": 3}})

    def test_list_is_owner_scoped_but_superuser_sees_all(self):
        mine = self._create_draft(resourceinstanceid=uuid.uuid4())
        ResourceDraft.objects.create(
            user=self.other_editor, graph_slug=SLUG, resourceinstanceid=uuid.uuid4()
        )
        # Editor sees only their own draft; superuser sees both.
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual({row["draftid"] for row in resp.json()}, {str(mine.pk)})
        self.idir_login_simulate(self.admin)
        self.assertEqual(len(self.client.get(self.list_url).json()), 2)

    def test_non_owner_cannot_access_draft(self):
        others = ResourceDraft.objects.create(
            user=self.other_editor, graph_slug=SLUG, data={"step1": {"x": 1}}
        )
        url = self._detail_url(others.pk)
        body = json.dumps({"data": {"step2": {"y": 2}}})
        for resp in (
            self.client.get(url),
            self.client.patch(url, data=body, content_type="application/json"),
            self.client.put(url, data=body, content_type="application/json"),
            self.client.delete(url),
        ):
            self.assertEqual(resp.status_code, 404)
        others.refresh_from_db()
        self.assertEqual(others.data, {"step1": {"x": 1}})  # untouched

    def test_graph_has_different_publication_flag(self):
        current = self._create_draft(
            graph_publication_id=get_current_graph(SLUG).publication_id,
            resourceinstanceid=uuid.uuid4(),
        )
        stale = self._create_draft(
            graph_publication_id=uuid.uuid4(), resourceinstanceid=uuid.uuid4()
        )
        self.assertFalse(
            self.client.get(self._detail_url(current.pk)).json()[
                "graph_has_different_publication"
            ]
        )
        self.assertTrue(
            self.client.get(self._detail_url(stale.pk)).json()[
                "graph_has_different_publication"
            ]
        )

    def test_delete_removes_draft(self):
        draft = self._create_draft()
        resp = self.client.delete(self._detail_url(draft.pk))
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(ResourceDraft.objects.filter(draftid=draft.pk).exists())

    def test_without_resource_editor_role_is_forbidden(self):
        # Drafts are editor-only on every verb, reads included.
        self.idir_login_simulate(self.user)
        self.assertEqual(self._post({"data": {}}).status_code, 403)
        self.assertEqual(self.client.get(self.list_url).status_code, 403)
