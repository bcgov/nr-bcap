"""End-to-end tests for the arches_querysets-native Process Requirement
resource endpoint: GET/PATCH the requirement and its sub-requirements through
the generic resource serializer (nested aliased_data), no custom service."""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from arches_querysets.models import ResourceTileTree

from bcap.util.bcap_aliases import GraphSlugs
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

        resource = ResourceTileTree.get_tiles(
            GraphSlugs.PROCESS_REQUIREMENT,
            resource_ids=[requirement.pk],
        ).get()
        ad = resource.aliased_data
        cls.ident_tileid = str(ad.requirement_identification.pk)
        cls.duration_tileid = str(ad.requirement_execution_duration.pk)
        cls.assessment_tileid = str(ad.sub_requirement_assessment_n1.pk)
        cls.sub_tileid = str(ad.sub_requirement[0].pk)

    def setUp(self):
        super().setUp()
        # Superuser satisfies ResourceEditor and has the editable_nodegroups
        # the nested tile save needs (a bare superuser's set is empty in the
        # test DB).
        self.admin = get_user_model().objects.get(username="admin")
        self.idir_login_simulate(self.admin)
        self.url = reverse("process_requirement", kwargs={"pk": self.resource_id})

    def _patch(self, payload):
        return self.client.patch(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def _aliased_data(self):
        """The current resource's aliased_data, read back via GET."""
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        return resp.json()["aliased_data"]

    def test_get_returns_200(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("aliased_data", body)
        data = body["aliased_data"]
        for key in (
            "requirement_identification",
            "requirement_execution_duration",
            "sub_requirement_assessment_n1",
            "sub_requirement",
        ):
            self.assertIn(key, data)

    def test_get_unknown_resource_returns_404(self):
        url = reverse("process_requirement", kwargs={"pk": UNKNOWN_ID})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_get_returns_identification_fields(self):
        ident = self._aliased_data()["requirement_identification"]["aliased_data"]
        req_id = ident["requirement_identification"]["display_value"]
        req_name = ident["requirement_name"]["display_value"]
        self.assertEqual(req_id, "REQ-1")
        self.assertEqual(req_name, "Review")

    def test_get_returns_execution_duration_fields(self):
        duration = self._aliased_data()["requirement_execution_duration"][
            "aliased_data"
        ]
        due = duration["requirement_process_due_date"]["display_value"]
        self.assertEqual(due, "2026-02-01")
        # start_date and completion_date not seeded - present but null
        self.assertIn("requirement_process_start_date", duration)
        self.assertIn("requirement_process_completion_date", duration)

    def test_get_returns_assessment_fields(self):
        assessment = self._aliased_data()["sub_requirement_assessment_n1"][
            "aliased_data"
        ]
        self.assertFalse(assessment["requirement_status"]["node_value"])
        notes = assessment["assessment_notes"]["display_value"]
        self.assertEqual(notes, "initial notes")

    def test_get_returns_sub_requirement_fields(self):
        sub = self._aliased_data()["sub_requirement"][0]["aliased_data"]
        self.assertEqual(sub["sub_requirement_name"]["display_value"], "Sub-1")
        self.assertEqual(
            sub["sub_requirement_description"]["display_value"],
            "Sub-1 description",
        )
        self.assertTrue(sub["sub_requirement_mandatory"]["node_value"])
        self.assertFalse(sub["sub_requirement_satisfied"]["node_value"])
        self.assertEqual(sub["sub_requirement_sort_order"]["node_value"], 1)

    def test_patch_sets_requirement_name(self):
        resp = self._patch(
            {
                "aliased_data": {
                    "requirement_identification": {
                        "tileid": self.ident_tileid,
                        "aliased_data": {
                            "requirement_identification": "REQ-2",
                            "requirement_name": "Updated Review",
                        },
                    }
                }
            }
        )
        self.assertEqual(resp.status_code, 200)
        after = self._aliased_data()["requirement_identification"]["aliased_data"]
        self.assertEqual(after["requirement_identification"]["display_value"], "REQ-2")
        self.assertEqual(after["requirement_name"]["display_value"], "Updated Review")

    def test_patch_sets_start_date(self):
        resp = self._patch(
            {
                "aliased_data": {
                    "requirement_execution_duration": {
                        "tileid": self.duration_tileid,
                        "aliased_data": {
                            "requirement_process_start_date": "2026-01-15"
                        },
                    }
                }
            }
        )
        self.assertEqual(resp.status_code, 200)
        after = self._aliased_data()["requirement_execution_duration"]["aliased_data"]
        self.assertEqual(
            after["requirement_process_start_date"]["display_value"],
            "2026-01-15",
        )

    def test_patch_sets_due_date(self):
        resp = self._patch(
            {
                "aliased_data": {
                    "requirement_execution_duration": {
                        "tileid": self.duration_tileid,
                        "aliased_data": {"requirement_process_due_date": "2026-12-31"},
                    }
                }
            }
        )
        self.assertEqual(resp.status_code, 200)
        after = self._aliased_data()["requirement_execution_duration"]["aliased_data"]
        self.assertEqual(
            after["requirement_process_due_date"]["display_value"],
            "2026-12-31",
        )

    def test_patch_sets_completion_date(self):
        # requirement_execution_duration is a cardinality-1 tile; the patch
        # must carry its tileid so the serializer updates it rather than
        # minting a second tile (which would trip a cardinality error).
        resp = self._patch(
            {
                "aliased_data": {
                    "requirement_execution_duration": {
                        "tileid": self.duration_tileid,
                        "aliased_data": {
                            "requirement_process_completion_date": "2026-03-01"
                        },
                    }
                }
            }
        )
        self.assertEqual(resp.status_code, 200)
        after = self._aliased_data()["requirement_execution_duration"]["aliased_data"]
        self.assertEqual(
            after["requirement_process_completion_date"]["display_value"],
            "2026-03-01",
        )

    def test_patch_sets_requirement_status(self):
        resp = self._patch(
            {
                "aliased_data": {
                    "sub_requirement_assessment_n1": {
                        "tileid": self.assessment_tileid,
                        "aliased_data": {"requirement_status": True},
                    }
                }
            }
        )
        self.assertEqual(resp.status_code, 200)
        after = self._aliased_data()["sub_requirement_assessment_n1"]["aliased_data"]
        self.assertTrue(after["requirement_status"]["node_value"])

    def test_patch_sets_assessment_notes(self):
        resp = self._patch(
            {
                "aliased_data": {
                    "sub_requirement_assessment_n1": {
                        "tileid": self.assessment_tileid,
                        "aliased_data": {"assessment_notes": "reviewed and approved"},
                    }
                }
            }
        )
        self.assertEqual(resp.status_code, 200)
        after = self._aliased_data()["sub_requirement_assessment_n1"]["aliased_data"]
        self.assertEqual(
            after["assessment_notes"]["display_value"], "reviewed and approved"
        )

    def test_patch_edits_sub_requirement(self):
        sub_tile_id = self.sub_tileid
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

    def test_patch_edits_sub_requirement_description(self):
        sub_tile_id = self.sub_tileid
        resp = self._patch(
            {
                "aliased_data": {
                    "sub_requirement": [
                        {
                            "tileid": sub_tile_id,
                            "aliased_data": {
                                "sub_requirement_name": "Sub-1",
                                "sub_requirement_description": "Updated",
                                "sub_requirement_sort_order": 1,
                            },
                        }
                    ]
                }
            }
        )
        self.assertEqual(resp.status_code, 200)
        sub = self._aliased_data()["sub_requirement"][0]
        self.assertEqual(
            sub["aliased_data"]["sub_requirement_description"]["display_value"],
            "Updated",
        )

    def test_patch_edits_sub_requirement_mandatory(self):
        sub_tile_id = self.sub_tileid
        resp = self._patch(
            {
                "aliased_data": {
                    "sub_requirement": [
                        {
                            "tileid": sub_tile_id,
                            "aliased_data": {
                                "sub_requirement_name": "Sub-1",
                                "sub_requirement_mandatory": False,
                                "sub_requirement_sort_order": 1,
                            },
                        }
                    ]
                }
            }
        )
        self.assertEqual(resp.status_code, 200)
        sub = self._aliased_data()["sub_requirement"][0]
        self.assertFalse(sub["aliased_data"]["sub_requirement_mandatory"]["node_value"])

    def test_patch_edits_sub_requirement_assessment_notes(self):
        sub_tile_id = self.sub_tileid
        resp = self._patch(
            {
                "aliased_data": {
                    "sub_requirement": [
                        {
                            "tileid": sub_tile_id,
                            "aliased_data": {
                                "sub_requirement_name": "Sub-1",
                                "sub_requirement_sort_order": 1,
                                "sub_requirement_assessment_notes": "ok",
                            },
                        }
                    ]
                }
            }
        )
        self.assertEqual(resp.status_code, 200)
        sub = self._aliased_data()["sub_requirement"][0]
        self.assertEqual(
            sub["aliased_data"]["sub_requirement_assessment_notes"]["display_value"],
            "ok",
        )

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
        url = reverse("process_requirement", kwargs={"pk": UNKNOWN_ID})
        resp = self.client.patch(url, data="{}", content_type="application/json")
        self.assertEqual(resp.status_code, 404)

    def test_patch_without_resource_editor_role_is_forbidden(self):
        self.idir_login_simulate(self.user)
        resp = self._patch({"aliased_data": {}})
        self.assertEqual(resp.status_code, 403)
