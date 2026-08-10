"""Tests for the generic per-user draft endpoints: a resource editor can POST a
draft, PATCH-merge sections into it, and DELETE it;
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

from arches_querysets.models import ResourceTileTree

from bcap.builders.contributor_builder import ContributorSpec
from bcap.services.contributor.organization_service import OrganizationService
from bcap.services.workflow_draft_service import WorkflowDraftService
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.controlled_list import reference_value
from bcap.util.graph import get_current_graph

from tests.builders import FixtureBuilder, request_as
from tests.controlled_list_fixtures import ControlledListFixtures
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
        # The list tests assert on whole lists, so they need users whose drafts
        # are only ever the ones they make themselves.
        cls.lister = User.objects.create_user(username="lister1", password="pass")
        cls.other_lister = User.objects.create_user(username="lister2", password="pass")
        cls.lister.groups.add(submitters)
        cls.other_lister.groups.add(submitters)
        cls.staff_lister = User.objects.create_user(username="lister3", password="pass")
        cls.staff_lister.groups.add(editors)
        # A real Contributor: the stamp is a resource-instance value, and a
        # reference to a resource that doesn't exist blows up on read.
        ControlledListFixtures.seed()
        cls.org = FixtureBuilder().make_contributor(
            ContributorSpec(
                reference_value("contributor", "contributor_type"), None, "Acme Corp"
            )
        )
        # cls.user (from AuthTestHelper) intentionally holds neither role.
        # Drafts to act on, made once: a create runs a full resource save, and
        # every test rolls back, so each test gets them untouched.
        cls.draft = cls._seed_draft(
            cls.editor,
            {"step1": {"x": 1}},
            publication_id=get_current_graph(SLUG).publication_id,
        )
        cls.stale_draft = cls._seed_draft(cls.editor, publication_id=uuid.uuid4())
        cls.applicant_draft = cls._seed_draft(cls.applicant, {"step1": {"x": 1}})
        cls.other_applicant_draft = cls._seed_draft(
            cls.other_applicant, {"step1": {"x": 1}}
        )

    @classmethod
    def _seed_draft(cls, user, data=None, publication_id=""):
        return WorkflowDraftService.record(
            WorkflowDraftService().create(
                request_as(user), SLUG, data or {}, publication_id=publication_id
            )
        )

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

    def _create_draft(
        self, user=None, data=None, publication_id="", organization_id=""
    ):
        return WorkflowDraftService.record(
            self.svc.create(
                request_as(user or self.editor),
                SLUG,
                data or {},
                publication_id=publication_id,
                organization_id=organization_id,
            )
        )

    def _save(self, pk, body):
        """PATCH the draft with the given body (data defaults to empty)."""
        return self.client.patch(
            self._detail_url(pk),
            data=json.dumps({"data": {}, **body}),
            content_type="application/json",
        )

    def _read(self, pk):
        """The stored draft as a fresh record. Bypasses the request layer and
        the visibility scoping, so it can assert on anyone's draft."""
        return WorkflowDraftService.record(
            ResourceTileTree.get_tiles(
                GraphSlugs.WORKFLOW_DRAFTS, as_representation=True
            ).get(pk=pk)
        )

    def _make_resource(self, owner):
        """A bare resource of the draft's graph, owned by the given user. Saved
        with descriptors, as every real save path leaves them."""
        resource = ResourceInstance.objects.create(
            graph_id=get_current_graph(SLUG).pk, descriptors={}
        )
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

    def test_patch_merges_sections_and_an_empty_one_clears_it(self):
        draft = self.draft
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
        # A section sent empty replaces what was there, which is how a caller
        # clears one without a whole-blob replace.
        resp = self.client.patch(
            self._detail_url(draft.id),
            data=json.dumps({"data": {"step1": {}}}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._read(draft.id).data, {"step1": {}, "step2": {"y": 2}})

    def test_patch_records_current_step_and_keeps_it_when_omitted(self):
        draft = self.draft
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

    def test_a_blank_step_clears_it_but_an_omitted_one_does_not(self):
        # Only None (an absent key) means "leave it alone"; "" is a real value
        # the client can send to unset the marker.
        draft = self.draft
        self._save(draft.id, {"current_step": "Contacts"})

        self._save(draft.id, {})
        self.assertEqual(self._read(draft.id).current_step, "Contacts")

        self._save(draft.id, {"current_step": ""})
        self.assertEqual(self._read(draft.id).current_step, "")

    def test_post_accepts_a_current_step_but_never_stores_it(self):
        # Pins current behaviour: the serializer allows the field, but create
        # doesn't write it, so a draft always starts with no step. Likely a bug.
        resp = self._post({"data": {}, "current_step": "Contacts"})

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["current_step"], "")
        self.assertEqual(self._read(resp.json()["id"]).current_step, "")

    def test_a_non_string_step_is_coerced(self):
        # The store only accepts a string, so the payload serializer settles it
        # before the save rather than letting the store raise mid-request.
        draft = self.draft

        resp = self._save(draft.id, {"current_step": 7})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._read(draft.id).current_step, "7")

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
        with patch("bcap.services.workflow_draft_service.datetime") as clock:
            clock.now.return_value = t1
            resp = self._post({"data": {"step1": {"x": 1}}})
        self.assertEqual(resp.status_code, 201)
        draft_id = resp.json()["id"]
        self.assertIsNotNone(resp.json()["updated"])
        self.assertEqual(datetime.fromisoformat(self._read(draft_id).updated), t1)

        # A later save advances the timestamp.
        with patch("bcap.services.workflow_draft_service.datetime") as clock:
            clock.now.return_value = t2
            resp = self.client.patch(
                self._detail_url(draft_id),
                data=json.dumps({"data": {"step2": {"y": 2}}}),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(datetime.fromisoformat(self._read(draft_id).updated), t2)

    def test_the_list_is_owner_scoped_for_staff_and_applicants_alike(self):
        self.idir_login_simulate(self.lister)
        resp = self._post({"data": {"step1": {"x": 1}}})
        self.assertEqual(resp.status_code, 201)
        mine = resp.json()["id"]
        self._create_draft(user=self.other_lister)

        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual({row["id"] for row in resp.json()}, {mine})
        # An unfinished form is its author's business, so staff get no widening.
        self.idir_login_simulate(self.staff_lister)
        self.assertEqual(self.client.get(self.list_url).json(), [])

    def test_drafts_stamped_for_my_organization_are_visible(self):
        """The stamp, not today's membership, is what a colleague matches on. Who
        belongs to which org is OrganizationService's business, so stub it."""
        outsider = get_user_model().objects.create_user(
            username="applicant3", password="pass"
        )
        outsider.groups.add(Group.objects.get(name="Submitter"))
        org_id = str(self.org.pk)
        members = {self.lister.username, self.other_lister.username}
        with patch.object(
            OrganizationService,
            "organization_ids",
            side_effect=lambda username: {org_id} if username in members else set(),
        ):
            mine = self._create_draft(user=self.lister, organization_id=org_id)
            colleague = self._create_draft(
                user=self.other_lister, organization_id=org_id
            )
            # Unstamped, and the outsider is in no org: theirs stays their own.
            self._create_draft(user=outsider)
            self.idir_login_simulate(self.lister)
            resp = self.client.get(self.list_url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual({row["id"] for row in resp.json()}, {mine.id, colleague.id})

    def test_an_unstamped_draft_stays_with_whoever_created_it(self):
        with patch.object(OrganizationService, "organization_ids", return_value=set()):
            mine = self._create_draft(user=self.lister)
            self._create_draft(user=self.other_lister)
            self.idir_login_simulate(self.lister)
            resp = self.client.get(self.list_url)

        self.assertEqual({row["id"] for row in resp.json()}, {mine.id})

    def test_a_draft_left_at_a_former_organization_is_no_longer_visible(self):
        """Creating it is not enough: the stamp hands the draft to the company,
        so leaving takes the author's own access with them."""
        org_id = str(self.org.pk)
        with patch.object(
            OrganizationService, "organization_ids", return_value={org_id}
        ):
            self._create_draft(user=self.lister, organization_id=org_id)
        with patch.object(OrganizationService, "organization_ids", return_value=set()):
            mine = self._create_draft(user=self.lister)
            self.idir_login_simulate(self.lister)
            resp = self.client.get(self.list_url)

        self.assertEqual({row["id"] for row in resp.json()}, {mine.id})

    def test_a_member_of_several_organizations_has_to_pick_one(self):
        both = {str(self.org.pk), str(uuid.uuid4())}
        with patch.object(OrganizationService, "organization_ids", return_value=both):
            resp = self._post({"data": {}})
            self.assertEqual(resp.status_code, 400)
            self.assertIn("organization_id", resp.json())
            # Picking one it is, then.
            resp = self._post({"data": {}, "organization_id": str(self.org.pk)})
            self.assertEqual(resp.status_code, 201)

    def test_a_draft_cannot_be_stamped_for_someone_elses_organization(self):
        with patch.object(OrganizationService, "organization_ids", return_value=set()):
            resp = self._post({"data": {}, "organization_id": str(self.org.pk)})
        self.assertEqual(resp.status_code, 403)

    def test_all_graphs_list_spans_graphs_and_stays_owner_scoped(self):
        self.idir_login_simulate(self.lister)
        mine = self._create_draft(user=self.lister)
        investigation = WorkflowDraftService.record(
            self.svc.create(
                request_as(self.lister),
                GraphSlugs.INVESTIGATION,
                {"step1": {"x": 1}},
            )
        )
        self._create_draft(user=self.other_lister)
        resp = self.client.get(reverse("workflow_draft_list_all"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            {row["id"] for row in resp.json()}, {mine.id, investigation.id}
        )

    def test_all_graphs_list_narrows_to_one_parent(self):
        permit = self._make_resource(self.editor)
        on_permit = WorkflowDraftService.record(
            self.svc.create(
                request_as(self.editor),
                GraphSlugs.INVESTIGATION,
                {},
                parent_resource_id=str(permit.pk),
            )
        )
        self._create_draft(user=self.other_editor)

        resp = self.client.get(
            reverse("workflow_draft_list_all"), {"parent": str(permit.pk)}
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual({row["id"] for row in resp.json()}, {on_permit.id})

    def test_non_owner_cannot_access_draft(self):
        self.idir_login_simulate(self.applicant)
        others = self.other_applicant_draft
        url = self._detail_url(others.id)
        body = json.dumps({"data": {"step2": {"y": 2}}})
        for resp in (
            self.client.get(url),
            self.client.patch(url, data=body, content_type="application/json"),
            self.client.delete(url),
        ):
            self.assertEqual(resp.status_code, 404)
        self.assertEqual(self._read(others.id).data, {"step1": {"x": 1}})  # untouched

    def test_graph_has_different_publication_flag(self):
        current, stale = self.draft, self.stale_draft
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
        draft = self.draft
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

    def test_saving_keeps_the_parent_resource(self):
        parent = self._make_resource(self.editor)
        draft_id = (
            self._post({"data": {}, "parent_resource_id": str(parent.pk)}).json()
        )["id"]
        resp = self.client.patch(
            self._detail_url(draft_id),
            data=json.dumps({"data": {"step1": {"x": 1}}}),
            content_type="application/json",
        )
        self.assertEqual(resp.json()["parent_resource_id"], str(parent.pk))

    def test_internal_staff_reach_no_verb_on_an_applicants_draft(self):
        # No internal-group widening on drafts: a Resource Editor is as walled
        # off from an applicant's unsubmitted form as another applicant is.
        draft = self.applicant_draft
        url = self._detail_url(draft.id)
        body = json.dumps({"data": {"step2": {"y": 2}}})

        for resp in (
            self.client.get(url),
            self.client.patch(url, data=body, content_type="application/json"),
            self.client.delete(url),
        ):
            self.assertEqual(resp.status_code, 404)
        self.assertEqual(self._read(draft.id).data, {"step1": {"x": 1}})

    def test_drafts_need_no_role_but_do_need_a_login(self):
        # Any signed-in user may keep drafts; owner scoping is what separates
        # them, not a role.
        self.idir_login_simulate(self.user)
        self.assertEqual(self._post({"data": {}}).status_code, 201)
        # Anonymous never reaches the view: auth middleware bounces it to login.
        self.client.logout()
        self.assertEqual(self._post({"data": {}}).status_code, 302)
        self.assertEqual(self.client.get(self.list_url).status_code, 302)
