"""The dedicated staff action routes for process requirements and modules:
- PATCH /process_requirement/<id>/status marks a requirement satisfied.
- PATCH /permit_application/<id>/module/<tileid> flips a module's completion,
  touching only the completion nodes so the module's order/name/id are kept.
Both are editor-only."""

import json
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from arches.app.models.models import TileModel

from bcap.util.aliases.permit_application import (
    PermitApplicationAliases as pa,
    PermitApplicationGroupAliases as pa_groups,
)
from bcap.util.aliases.process_requirement import (
    ProcessRequirementAliases as prq,
    ProcessRequirementGroupAliases as prq_groups,
)
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import node_id
from bcap.builders.process_requirement_builder import ProcessRequirementBuilder
from tests.builders import FixtureBuilder
from tests.views.helpers import AuthTestHelper

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def _make_requirement(satisfied):
    """A checklist process requirement with its assessment status preset."""
    return ProcessRequirementBuilder().make_process_requirement(
        {
            "id": "REQ-1",
            "name": "Review",
            "due": "2026-02-01",
            "notes": "",
            "satisfied": satisfied,
            "sub_requirements": [],
        }
    )


def _requirement_status(requirement_id):
    """The stored requirement_status on the assessment tile, or None if unset."""
    ngid = node_id(
        GraphSlugs.PROCESS_REQUIREMENT, prq_groups.SUB_REQUIREMENT_ASSESSMENT_N1
    )
    nodeid = node_id(GraphSlugs.PROCESS_REQUIREMENT, prq.REQUIREMENT_STATUS)
    tile = TileModel.objects.filter(
        resourceinstance_id=requirement_id, nodegroup_id=ngid
    ).first()
    return None if tile is None else tile.data.get(nodeid)


@override_settings(ROOT_URLCONF="tests.test_urls")
class RequirementStatusRouteTests(AuthTestHelper, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin = get_user_model().objects.get(username="admin")
        cls.requirement_id = str(_make_requirement(satisfied=False).pk)

    def setUp(self):
        super().setUp()
        self.idir_login_simulate(self.admin)
        self.url = reverse(
            "requirement_status", kwargs={"requirement_id": self.requirement_id}
        )

    def _patch(self, payload, url=None):
        return self.client.patch(
            url or self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_patch_marks_satisfied(self):
        resp = self._patch({"satisfied": True})
        self.assertEqual(resp.status_code, 204)
        self.assertIs(_requirement_status(self.requirement_id), True)

    def test_patch_marks_unsatisfied(self):
        self._patch({"satisfied": True})
        resp = self._patch({"satisfied": False})
        self.assertEqual(resp.status_code, 204)
        self.assertIs(_requirement_status(self.requirement_id), False)

    def test_unknown_requirement_returns_404(self):
        url = reverse("requirement_status", kwargs={"requirement_id": UNKNOWN_ID})
        self.assertEqual(self._patch({"satisfied": True}, url=url).status_code, 404)

    def test_missing_body_is_a_400(self):
        self.assertEqual(self._patch({}).status_code, 400)

    def test_requires_resource_editor(self):
        self.idir_login_simulate(self.user)  # not a Resource Editor
        self.assertEqual(self._patch({"satisfied": True}).status_code, 403)


@override_settings(ROOT_URLCONF="tests.test_urls")
class ModuleCompletionRouteTests(AuthTestHelper, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin = get_user_model().objects.get(username="admin")
        cls.editor = get_user_model().objects.create_user(
            username="mod-editor", password="pass"
        )
        cls.editor.groups.add(Group.objects.get(name="Resource Editor"))

        builder = FixtureBuilder()
        permit = builder.new_resource("permit_application")
        permit.append_tile("application_admin")
        admin = permit.aliased_data.application_admin
        builder.prune_blank_tiles(admin, pa_groups.PROCESS_MODULE, pa.MODULE_NAME)
        cls.module_name = "Permit Application"
        cls.module_id = str(uuid4())
        cls.module_order = 3
        builder.append_blank_tile_for_group(
            admin,
            pa_groups.PROCESS_MODULE,
            {
                pa.MODULE_NAME: builder.localized(cls.module_name),
                pa.MODULE_ID: cls.module_id,
                pa.MODULE_ORDER: cls.module_order,
            },
        )
        permit.save(**builder.save_kwargs)
        cls.permit_id = str(permit.pk)
        cls.module_tileid = str(admin.aliased_data.process_module[0].pk)

    def setUp(self):
        super().setUp()
        self.idir_login_simulate(self.admin)

    def _url(self, permit_id=None, module_tileid=None):
        return reverse(
            "permit_module",
            kwargs={
                "pk": permit_id or self.permit_id,
                "module_tileid": module_tileid or self.module_tileid,
            },
        )

    def _patch(self, payload, url=None):
        return self.client.patch(
            url or self._url(),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def _module_tile(self):
        return TileModel.objects.get(pk=self.module_tileid)

    def _node(self, alias):
        return node_id(GraphSlugs.PERMIT_APPLICATION, alias)

    def test_patch_completes_and_stamps_date(self):
        resp = self._patch({"completed": True})
        self.assertEqual(resp.status_code, 204)
        data = self._module_tile().data
        self.assertIs(data.get(self._node(pa.IS_MODULE_COMPLETED)), True)
        self.assertIsNotNone(data.get(self._node(pa.MODULE_COMPLETED_DATE)))

    def test_patch_uncompletes_and_clears_date(self):
        self._patch({"completed": True})
        resp = self._patch({"completed": False})
        self.assertEqual(resp.status_code, 204)
        data = self._module_tile().data
        self.assertIs(data.get(self._node(pa.IS_MODULE_COMPLETED)), False)
        self.assertIsNone(data.get(self._node(pa.MODULE_COMPLETED_DATE)))

    def test_completion_preserves_order_name_and_id(self):
        self._patch({"completed": True})
        data = self._module_tile().data
        self.assertEqual(data.get(self._node(pa.MODULE_ORDER)), self.module_order)
        self.assertEqual(data.get(self._node(pa.MODULE_ID)), self.module_id)
        name = data.get(self._node(pa.MODULE_NAME))
        self.assertEqual(name["en"]["value"], self.module_name)

    def test_unknown_module_returns_404(self):
        self.assertEqual(
            self._patch(
                {"completed": True}, url=self._url(module_tileid=UNKNOWN_ID)
            ).status_code,
            404,
        )

    def test_unknown_permit_returns_404(self):
        self.assertEqual(
            self._patch(
                {"completed": True}, url=self._url(permit_id=UNKNOWN_ID)
            ).status_code,
            404,
        )

    def test_requires_resource_editor(self):
        self.idir_login_simulate(self.user)  # not a Resource Editor
        self.assertEqual(self._patch({"completed": True}).status_code, 403)
