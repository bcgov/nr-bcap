"""End-to-end tests for the Permit Application create endpoint: POSTing a new
application clones the process-requirement templates into fresh working copies
and attaches them in flow order, and a validation failure rolls those copies
back."""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from arches_querysets.models import ResourceTileTree

from bcap.util.aliases.permit_application import (
    PermitApplicationAliases as aliases,
    PermitApplicationGroupAliases as group_aliases,
)
from bcap.util.bcap_aliases import ALIASED_DATA, GraphSlugs
from bcap.util.dashboard.resource_builder import ResourceBuilder

from tests.permit_fixtures import seed_requirement_templates
from tests.views.helpers import AuthTestHelper


def admin_only_payload():
    """The minimum a create needs: an empty application_admin tile for the
    create hook to attach process requirements to."""
    return {ALIASED_DATA: {group_aliases.APPLICATION_ADMIN: {ALIASED_DATA: {}}}}


@override_settings(ROOT_URLCONF="tests.test_urls")
class PermitApplicationCreateViewTests(AuthTestHelper, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        templates = seed_requirement_templates(ResourceBuilder())
        cls.template_pks = {str(template.pk) for template in templates}

    def setUp(self):
        super().setUp()
        self.admin = get_user_model().objects.get(username="admin")
        self.idir_login_simulate(self.admin)
        self.url = reverse("permit_application_create")

    def _post(self, payload):
        return self.client.post(
            self.url, data=json.dumps(payload), content_type="application/json"
        )

    def _requirement_count(self):
        return ResourceTileTree.get_tiles(GraphSlugs.PROCESS_REQUIREMENT).count()

    def _process_requirements(self, permit_id):
        permit = ResourceTileTree.get_tiles(
            GraphSlugs.PERMIT_APPLICATION, resource_ids=[permit_id]
        ).get()
        return permit.aliased_data.application_admin.aliased_data.process_requirement

    def test_post_attaches_a_fresh_working_copy_per_template(self):
        resp = self._post(admin_only_payload())
        self.assertEqual(resp.status_code, 201)

        children = self._process_requirements(resp.json()["resourceinstanceid"])
        self.assertEqual(len(children), 3)
        for child in children:
            requirement_id = str(child.aliased_data.process_requirement.pk)
            # A clone, not the template it was copied from.
            self.assertNotIn(requirement_id, self.template_pks)
            requirement = ResourceTileTree.get_tiles(
                GraphSlugs.PROCESS_REQUIREMENT, resource_ids=[requirement_id]
            ).get()
            ident = requirement.aliased_data.requirement_identification.aliased_data
            self.assertFalse(
                ident.is_template_requirement.aliased_data.is_template_requirement
            )

    def test_validation_failure_rolls_back_requirements(self):
        before = self._requirement_count()
        payload = admin_only_payload()
        # application_id and project_name are required; a present tile with them
        # null fails validation after the requirements have been cloned.
        payload[ALIASED_DATA][group_aliases.APPLICATION_IDENTIFICATION] = {
            ALIASED_DATA: {aliases.APPLICATION_ID: None, aliases.PROJECT_NAME: None}
        }
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self._requirement_count(), before)

    def test_post_without_resource_editor_role_is_forbidden(self):
        self.idir_login_simulate(self.user)
        resp = self._post(admin_only_payload())
        self.assertEqual(resp.status_code, 403)
