"""End-to-end tests for the arches_querysets-native Process Requirement
resource endpoint: GET/PATCH the requirement and its sub-requirements through
the generic resource serializer (nested aliased_data), no custom service."""

import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from arches_querysets.models import ResourceTileTree

from bcap.util.aliases.process_requirement import (
    ProcessRequirementAliases as aliases,
    ProcessRequirementGroupAliases as groups,
)
from bcap.util.bcap_aliases import ALIASED_DATA, GraphSlugs
from bcap.util.dashboard.resource_builder import ResourceBuilder
from tests.views.helpers import AuthTestHelper


def make_requirement(builder, subs=()):
    """A process requirement due 2026-02-01 with the given sub-requirements,
    each a (name, satisfied, sort_order) tuple."""
    return builder.make_process_requirement(
        {
            "id": "REQ-1",
            "name": "Review",
            "due": "2026-02-01",
            "notes": "initial notes",
            "satisfied": False,
            "sub_requirements": [
                {
                    "name": name,
                    "description": f"{name} description",
                    "mandatory": True,
                    "sub_satisfied": satisfied,
                    "sort_order": sort_order,
                }
                for name, satisfied, sort_order in subs
            ],
        }
    )


UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


@override_settings(ROOT_URLCONF="tests.test_urls")
class ProcessRequirementViewTests(AuthTestHelper, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        requirement = make_requirement(ResourceBuilder(), subs=[("Sub-1", False, 1)])
        cls.resource_id = str(requirement.pk)
        cls.editor = get_user_model().objects.create_user(
            username="pr-editor", password="pass"
        )
        cls.editor.groups.add(Group.objects.get(name="Resource Editor"))

        resource = ResourceTileTree.get_tiles(
            GraphSlugs.PROCESS_REQUIREMENT,
            resource_ids=[requirement.pk],
        ).get()
        ad = resource.aliased_data
        cls.ident_tileid = str(ad.requirement_identification.pk)
        cls.requirement_data_tileid = str(ad.requirement_data.pk)
        cls.sub_tileid = str(ad.requirement_data.aliased_data.sub_requirement_n1[0].pk)

    def setUp(self):
        super().setUp()
        # Superuser satisfies ResourceEditor and has the editable_nodegroups
        # the nested tile save needs (a bare superuser's set is empty in the
        # test DB).
        self.admin = get_user_model().objects.get(username="admin")
        self.idir_login_simulate(self.admin)
        self.url = reverse("api_process_requirement", kwargs={"pk": self.resource_id})

    def _patch(self, payload):
        return self.client.patch(
            self.url, data=json.dumps(payload), content_type="application/json"
        )

    def _aliased_data(self):
        """The current resource's aliased_data, read back via GET."""
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        return resp.json()[ALIASED_DATA]

    def test_get_returns_requirement(self):
        data = self._aliased_data()
        ident = data[aliases.REQUIREMENT_IDENTIFICATION][ALIASED_DATA]
        self.assertEqual(
            ident[aliases.REQUIREMENT_IDENTIFICATION]["display_value"], "REQ-1"
        )
        self.assertEqual(ident[aliases.REQUIREMENT_NAME]["display_value"], "Review")
        duration = data[groups.REQUIREMENT_EXECUTION_DURATION][ALIASED_DATA]
        self.assertEqual(
            duration[aliases.REQUIREMENT_PROCESS_DUE_DATE]["display_value"],
            "2026-02-01",
        )
        sub = data[groups.REQUIREMENT_DATA][ALIASED_DATA][groups.SUB_REQUIREMENT_N1][0][
            ALIASED_DATA
        ]
        self.assertEqual(sub[aliases.CHECKLIST_ITEM_NAME]["display_value"], "Sub-1")

    def test_get_unknown_resource_returns_404(self):
        url = reverse("api_process_requirement", kwargs={"pk": UNKNOWN_ID})
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_resource_editor_can_view_requirement_they_do_not_own(self):
        self.idir_login_simulate(self.editor)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_non_owner_without_editor_role_cannot_view(self):
        self.idir_login_simulate(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_patch_updates_fields(self):
        # Cardinality-1 tiles carry their tileid so the serializer updates the
        # existing tile; a list tile is validated as a whole card, so its
        # required nodes (name + sort order) accompany the edited field.
        resp = self._patch(
            {
                ALIASED_DATA: {
                    aliases.REQUIREMENT_IDENTIFICATION: {
                        "tileid": self.ident_tileid,
                        ALIASED_DATA: {
                            aliases.REQUIREMENT_IDENTIFICATION: "REQ-2",
                            aliases.REQUIREMENT_NAME: "Updated Review",
                        },
                    },
                    groups.REQUIREMENT_DATA: {
                        "tileid": self.requirement_data_tileid,
                        ALIASED_DATA: {
                            groups.SUB_REQUIREMENT_N1: [
                                {
                                    "tileid": self.sub_tileid,
                                    ALIASED_DATA: {
                                        aliases.CHECKLIST_ITEM_NAME: "Sub-1",
                                        aliases.CHECKLIST_ITEM_SORT_ORDER: 1,
                                        aliases.CHECKLIST_ITEM_COMPLETED: True,
                                    },
                                }
                            ]
                        },
                    },
                }
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = self._aliased_data()
        ident = data[aliases.REQUIREMENT_IDENTIFICATION][ALIASED_DATA]
        self.assertEqual(
            ident[aliases.REQUIREMENT_IDENTIFICATION]["display_value"], "REQ-2"
        )
        self.assertEqual(
            ident[aliases.REQUIREMENT_NAME]["display_value"], "Updated Review"
        )
        sub = data[groups.REQUIREMENT_DATA][ALIASED_DATA][groups.SUB_REQUIREMENT_N1][0][
            ALIASED_DATA
        ]
        self.assertTrue(sub[aliases.CHECKLIST_ITEM_COMPLETED]["node_value"])

    def test_patch_unknown_resource_returns_404(self):
        url = reverse("api_process_requirement", kwargs={"pk": UNKNOWN_ID})
        resp = self.client.patch(url, data="{}", content_type="application/json")
        self.assertEqual(resp.status_code, 404)

    def test_patch_by_non_owner_returns_404(self):
        self.idir_login_simulate(self.user)
        resp = self._patch({ALIASED_DATA: {}})
        self.assertEqual(resp.status_code, 404)
