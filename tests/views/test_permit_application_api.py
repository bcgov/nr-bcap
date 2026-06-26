"""End-to-end tests for the Permit Application endpoints: POST creates an
application and seeds its id; the update that first sets the submission date
attaches the process-requirement working copies."""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from arches_querysets.models import ResourceTileTree

from bcap.services.dashboard.dashboard_types import DashboardFilter
from bcap.services.dashboard.internal_dashboard_service import (
    InternalDashboardService,
)
from bcap.services.permit_application.permit_application_service import (
    PermitApplicationService,
)
from bcap.util.aliases.permit_application import (
    PermitApplicationAliases as aliases,
    PermitApplicationGroupAliases as group_aliases,
)
from bcap.util.bcap_aliases import ALIASED_DATA, GraphSlugs
from bcap.util.dashboard.resource_builder import ResourceBuilder
from bcap.util.i18n import localized_string

from tests.permit_fixtures import seed_requirement_templates
from tests.views.helpers import AuthTestHelper


def create_payload():
    """A create body: the identification tile the seeded id shares with the
    required project_name."""
    return {
        ALIASED_DATA: {
            group_aliases.APPLICATION_IDENTIFICATION: {
                ALIASED_DATA: {aliases.PROJECT_NAME: "Test Project"}
            }
        }
    }


def submission_payload():
    """An update that sets the submission date."""
    return {
        ALIASED_DATA: {
            group_aliases.APPLICATION_ADMIN: {
                ALIASED_DATA: {aliases.APPLICATION_SUBMISSION_DATE: "2026-06-18"}
            }
        }
    }


@override_settings(ROOT_URLCONF="tests.test_urls")
class PermitApplicationTests(AuthTestHelper, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        seed_requirement_templates(ResourceBuilder())

    def setUp(self):
        super().setUp()
        self.idir_login_simulate(get_user_model().objects.get(username="admin"))

    def _post(self, payload):
        return self.client.post(
            reverse("permit_application_create"),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def _patch(self, pk, payload):
        return self.client.patch(
            reverse("api_permit_application", args=[pk]),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def _get(self, pk):
        return self.client.get(reverse("api_permit_application", args=[pk])).json()

    def _put(self, pk, payload):
        return self.client.put(
            reverse("api_permit_application", args=[pk]),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def _create(self):
        resp = self._post(create_payload())
        self.assertEqual(resp.status_code, 201)
        return resp.json()["resourceinstanceid"]

    def _permit(self, pk):
        return ResourceTileTree.get_tiles(
            GraphSlugs.PERMIT_APPLICATION, resource_ids=[pk]
        ).get()

    def _requirements(self, pk):
        admin = self._permit(pk).aliased_data.application_admin
        return admin.aliased_data.process_requirement if admin else []

    def _application_id(self, pk):
        ident = self._permit(pk).aliased_data.application_identification
        return localized_string(ident.aliased_data.application_id) if ident else ""

    def _requirement_count(self):
        return ResourceTileTree.get_tiles(GraphSlugs.PROCESS_REQUIREMENT).count()

    def test_create_seeds_distinct_ids_without_requirements(self):
        first, second = self._create(), self._create()
        self.assertRegex(self._application_id(first), r"^APP-\d+$")
        self.assertRegex(self._application_id(second), r"^APP-\d+$")
        self.assertNotEqual(self._application_id(first), self._application_id(second))
        self.assertEqual(self._requirements(first), [])

    def test_draft_without_submission_date_is_hidden_from_dashboard(self):
        pk = self._create()
        page = InternalDashboardService().get_cards(DashboardFilter())
        self.assertNotIn(pk, [card.id for card in page.results])

    def test_create_with_submission_date_attaches_requirements(self):
        payload = create_payload()
        payload[ALIASED_DATA][group_aliases.APPLICATION_ADMIN] = {
            ALIASED_DATA: {aliases.APPLICATION_SUBMISSION_DATE: "2026-06-18"}
        }
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(self._requirements(resp.json()["resourceinstanceid"])), 3)

    def test_submission_via_put_attaches_requirements(self):
        pk = self._create()
        # Round-trip the resource (so tile ids are preserved), set the date,
        # and PUT it back.
        body = self._get(pk)
        body[ALIASED_DATA][group_aliases.APPLICATION_ADMIN] = {
            ALIASED_DATA: {aliases.APPLICATION_SUBMISSION_DATE: "2026-06-18"}
        }
        self.assertEqual(self._put(pk, body).status_code, 200)
        self.assertEqual(len(self._requirements(pk)), 3)

    def test_resubmission_does_not_reattach_requirements(self):
        pk = self._create()
        self._patch(pk, submission_payload())
        before = self._requirement_count()

        # Already submitted, so a further submit clones nothing; it just saves.
        saved = []
        PermitApplicationService().submit(
            self._permit(pk), submission_payload(), lambda: saved.append(True)
        )
        self.assertTrue(saved)
        self.assertEqual(self._requirement_count(), before)

    def test_failed_submission_rolls_back_requirements(self):
        pk = self._create()
        before = self._requirement_count()
        # Sets the submission date (so requirements clone) but nulls the
        # required project_name, so the save is rejected.
        payload = submission_payload()
        payload[ALIASED_DATA][group_aliases.APPLICATION_IDENTIFICATION] = {
            ALIASED_DATA: {aliases.PROJECT_NAME: None}
        }
        self.assertEqual(self._patch(pk, payload).status_code, 400)
        self.assertEqual(self._requirement_count(), before)

    def test_create_forbidden_without_resource_editor_role(self):
        self.idir_login_simulate(self.user)
        self.assertEqual(self._post(create_payload()).status_code, 403)

    def _nesting_variants(self, group):
        """A body missing the tree at each level: no aliased_data, no group,
        group without aliased_data, and full nesting."""
        return [
            {},
            {ALIASED_DATA: {}},
            {ALIASED_DATA: {group: {}}},
            {ALIASED_DATA: {group: {ALIASED_DATA: {}}}},
        ]

    def test_assign_id_builds_every_identification_nesting(self):
        group = group_aliases.APPLICATION_IDENTIFICATION
        for body in self._nesting_variants(group):
            with self.subTest(body=body):
                PermitApplicationService()._assign_application_id(body)
                ident = body[ALIASED_DATA][group][ALIASED_DATA]
                self.assertRegex(ident[aliases.APPLICATION_ID], r"^APP-\d+$")

    def test_inject_requirements_builds_every_admin_nesting(self):
        group = group_aliases.APPLICATION_ADMIN
        for body in self._nesting_variants(group):
            with self.subTest(body=body):
                service = PermitApplicationService()
                copies = service._inject_requirements_from_templates(body)
                admin = body[ALIASED_DATA][group][ALIASED_DATA]
                self.assertEqual(len(admin[aliases.PROCESS_REQUIREMENT]), len(copies))
