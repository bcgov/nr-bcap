"""End-to-end tests for the Process Requirement PATCH endpoint: view ->
serializer -> service, against a real requirement and an authenticated session."""

import json
from dataclasses import asdict
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from bcap.serializers.process_requirement_serializers import (
    ProcessRequirementSerializer,
)
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.services.process_requirement.process_requirement_types import (
    ProcessRequirement,
    SubRequirement,
)
from bcap.util.dashboard.resource_builder import ResourceBuilder
from tests.services.test_process_requirement_service import make_requirement
from tests.views.helpers import AuthTestHelper

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


@override_settings(ROOT_URLCONF="tests.test_urls")
class ProcessRequirementWriteViewTests(AuthTestHelper, TestCase):
    @classmethod
    def setUpTestData(cls):
        # Rolled back with the class transaction.
        requirement = make_requirement(ResourceBuilder(), subs=[("Sub-1", False, 1)])
        cls.resource_id = str(requirement.pk)
        service = ProcessRequirementService()
        out = service.to_output(service.get_queryset().get(pk=requirement.pk))
        cls.sub_id = out.sub_requirements[0].id

    def setUp(self):
        super().setUp()
        # The seeded admin has the resource-edit permissions the save needs (a
        # bare superuser's editable_nodegroups is empty in the test DB), and as
        # a superuser it satisfies the ResourceEditor permission class.
        self.admin = get_user_model().objects.get(username="admin")
        self.idir_login_simulate(self.admin)
        self.url = reverse(
            "process_requirement_write", kwargs={"resource_id": self.resource_id}
        )

    def _patch(self, payload):
        return self.client.patch(
            self.url,
            data=json.dumps(payload, default=str),  # date -> "YYYY-MM-DD"
            content_type="application/json",
        )

    def _object(self, resp):
        """The response body parsed back into a ProcessRequirement."""
        serializer = ProcessRequirementSerializer(data=resp.json())
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def test_patch_sets_dates_and_returns_object(self):
        resp = self._patch(
            {"start_date": "2026-01-01", "completion_date": "2026-03-01"}
        )
        self.assertEqual(resp.status_code, 200)
        result = self._object(resp)
        self.assertEqual(result.id, self.resource_id)
        self.assertEqual(result.start_date, date(2026, 1, 1))
        self.assertEqual(result.completion_date, date(2026, 3, 1))
        self.assertEqual(result.due_date, date(2026, 2, 1))  # untouched

    def test_patch_edits_sub_requirement(self):
        resp = self._patch(
            {
                "sub_requirements": [
                    {"id": self.sub_id, "satisfied": True, "assessment_notes": "done"}
                ]
            }
        )
        self.assertEqual(resp.status_code, 200)
        sub = self._object(resp).sub_requirements[0]
        self.assertEqual(sub.id, self.sub_id)
        self.assertTrue(sub.satisfied)
        self.assertEqual(sub.assessment_notes, "done")

    def test_patch_adds_sub_requirement_without_id(self):
        resp = self._patch(
            {
                "sub_requirements": [
                    {
                        "name": "Added",
                        "satisfied": True,
                        "assessment_notes": "added",
                        "sort_order": 2,
                    }
                ]
            }
        )
        self.assertEqual(resp.status_code, 200)
        subs = self._object(resp).sub_requirements
        self.assertEqual(len(subs), 2)  # the seeded one plus the new one
        added = next(s for s in subs if s.id != self.sub_id)
        self.assertEqual(added.name, "Added")
        self.assertTrue(added.satisfied)
        self.assertEqual(added.assessment_notes, "added")
        self.assertEqual(added.sort_order, 2)

    def test_patch_add_sub_requirement_without_name_returns_400(self):
        resp = self._patch({"sub_requirements": [{"satisfied": True, "sort_order": 2}]})
        self.assertEqual(resp.status_code, 400)

    def test_patch_add_sub_requirement_without_sort_order_returns_400(self):
        resp = self._patch({"sub_requirements": [{"name": "Added"}]})
        self.assertEqual(resp.status_code, 400)

    def test_patch_all_fields(self):
        payload = asdict(
            ProcessRequirement(
                start_date=date(2026, 1, 1),
                due_date=date(2026, 2, 10),
                completion_date=date(2026, 3, 1),
                sub_requirements=[
                    SubRequirement(
                        id=self.sub_id,
                        satisfied=True,
                        assessment_notes="all done",
                        sort_order=7,
                    )
                ],
            )
        )
        resp = self._patch(payload)
        self.assertEqual(resp.status_code, 200)
        result = self._object(resp)
        self.assertEqual(result.id, self.resource_id)
        self.assertEqual(result.start_date, date(2026, 1, 1))
        self.assertEqual(result.due_date, date(2026, 2, 10))
        self.assertEqual(result.completion_date, date(2026, 3, 1))
        sub = result.sub_requirements[0]
        self.assertEqual(sub.id, self.sub_id)
        self.assertTrue(sub.satisfied)
        self.assertEqual(sub.assessment_notes, "all done")
        self.assertEqual(sub.sort_order, 7)

    def test_patch_null_clears_a_date(self):
        # The requirement starts with a due date; an explicit null clears it,
        # while the other (omitted) dates are left untouched.
        resp = self._patch({"due_date": None})
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(self._object(resp).due_date)

    def test_patch_invalid_date_returns_400(self):
        # The date fields validate format; a bad date is rejected before save.
        resp = self._patch({"start_date": "2026-13-99"})
        self.assertEqual(resp.status_code, 400)

    def test_patch_unknown_sub_requirement_returns_404(self):
        # The id isn't on this resource (e.g. deleted since the client loaded
        # it); the service raises StaleReference, which the view maps to 404.
        resp = self._patch(
            {"sub_requirements": [{"id": UNKNOWN_ID, "satisfied": True}]}
        )
        self.assertEqual(resp.status_code, 404)

    def test_patch_unknown_resource_returns_404(self):
        url = reverse("process_requirement_write", kwargs={"resource_id": UNKNOWN_ID})
        resp = self.client.patch(url, data="{}", content_type="application/json")
        self.assertEqual(resp.status_code, 404)

    def test_patch_without_resource_editor_role_is_forbidden(self):
        # A plain authenticated user (not a Resource Editor / superuser).
        self.idir_login_simulate(self.user)
        resp = self._patch({"start_date": "2026-01-01"})
        self.assertEqual(resp.status_code, 403)

    def test_get_is_not_allowed(self):
        # The endpoint only defines patch().
        self.assertEqual(self.client.get(self.url).status_code, 405)
