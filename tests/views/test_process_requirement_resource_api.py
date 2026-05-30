"""End-to-end tests for the arches_querysets-native Process Requirement
resource endpoint: GET/PATCH the requirement and its sub-requirements through
the generic resource serializer (nested aliased_data), no custom service."""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from bcap.util.dashboard.resource_builder import ResourceBuilder
from tests.services.test_process_requirement_service import make_requirement
from tests.views.helpers import AuthTestHelper

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


@override_settings(ROOT_URLCONF="tests.test_urls")
class ProcessRequirementResourceViewTests(AuthTestHelper, TestCase):
    @classmethod
    def setUpTestData(cls):
        requirement = make_requirement(ResourceBuilder(), subs=[("Sub-1", False, 1)])
        cls.resource_id = str(requirement.pk)

    def setUp(self):
        super().setUp()
        # Superuser satisfies ResourceEditor and has the editable_nodegroups the
        # nested tile save needs (a bare superuser's set is empty in the test DB).
        self.admin = get_user_model().objects.get(username="admin")
        self.idir_login_simulate(self.admin)
        self.url = reverse(
            "process_requirement_resource", kwargs={"pk": self.resource_id}
        )

    def _patch(self, payload):
        return self.client.patch(
            self.url, data=json.dumps(payload), content_type="application/json"
        )

    def _aliased_data(self):
        """The current resource's aliased_data, read back via GET."""
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        return resp.json()["aliased_data"]

    def test_get_returns_nested_tile_tree(self):
        data = self._aliased_data()
        sub = data["sub_requirement"][0]
        # Nodes serialize in arches representation form (node_value/display_value).
        self.assertEqual(
            sub["aliased_data"]["sub_requirement_name"]["display_value"], "Sub-1"
        )

    def test_patch_sets_completion_date(self):
        # requirement_execution_duration is a cardinality-1 tile; the patch must
        # carry its tileid so the serializer updates it rather than minting a
        # second tile (which would trip a cardinality error).
        dates = self._aliased_data()["requirement_execution_duration"]
        resp = self._patch(
            {
                "aliased_data": {
                    "requirement_execution_duration": {
                        "tileid": dates["tileid"],
                        "aliased_data": {
                            "requirement_process_completion_date": "2026-03-01"
                        },
                    }
                }
            }
        )
        self.assertEqual(resp.status_code, 200)
        dates = self._aliased_data()["requirement_execution_duration"]["aliased_data"]
        self.assertEqual(
            dates["requirement_process_completion_date"]["display_value"], "2026-03-01"
        )

    def test_patch_edits_sub_requirement(self):
        sub_tile_id = self._aliased_data()["sub_requirement"][0]["tileid"]
        # Each tile in the list is validated as a whole card, so the card's
        # required nodes (name + sort order) must accompany the edited field.
        resp = self._patch(
            {
                "aliased_data": {
                    "sub_requirement": [
                        {
                            "tileid": sub_tile_id,
                            "aliased_data": {
                                "sub_requirement_satisfied": True,
                                "sub_requirement_name": "Sub-1",
                                "sub_requirement_sort_order": 1,
                            },
                        }
                    ]
                }
            }
        )
        self.assertEqual(resp.status_code, 200)
        sub = self._aliased_data()["sub_requirement"][0]
        self.assertEqual(sub["tileid"], sub_tile_id)
        self.assertTrue(sub["aliased_data"]["sub_requirement_satisfied"]["node_value"])

    def test_patch_adds_sub_requirement(self):
        resp = self._patch(
            {
                "aliased_data": {
                    "sub_requirement": [
                        {
                            "aliased_data": {
                                "sub_requirement_name": "Sub-2",
                                "sub_requirement_sort_order": 2,
                            }
                        }
                    ]
                }
            }
        )
        self.assertEqual(resp.status_code, 200)
        names = {
            s["aliased_data"]["sub_requirement_name"]["display_value"]
            for s in self._aliased_data()["sub_requirement"]
        }
        self.assertIn("Sub-2", names)

    def test_patch_unknown_resource_returns_404(self):
        url = reverse("process_requirement_resource", kwargs={"pk": UNKNOWN_ID})
        resp = self.client.patch(url, data="{}", content_type="application/json")
        self.assertEqual(resp.status_code, 404)

    def test_patch_without_resource_editor_role_is_forbidden(self):
        self.idir_login_simulate(self.user)
        resp = self._patch({"aliased_data": {}})
        self.assertEqual(resp.status_code, 403)
