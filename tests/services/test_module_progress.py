"""Tests for the dashboards' shared module-completion helper: per-permit module
name and completion, read off an already-loaded permit tree."""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from arches.app.models.models import TileModel

from arches_querysets.models import ResourceTileTree

from bcap.util.graph import node_info
from bcap.services.dashboard.base_dashboard_service import BaseDashboardService
from bcap.builders.process_requirement_builder import ProcessRequirementBuilder
from bcap.util.aliases.permit_application import PermitApplicationAliases as pa
from bcap.util.bcap_aliases import GraphSlugs
from tests.permit_fixtures import seed_requirement_templates
from tests.views.helpers import AuthTestHelper
from tests.views.test_permit_application_api import create_payload, submission_payload


@override_settings(ROOT_URLCONF="tests.test_urls")
class ModuleProgressTests(AuthTestHelper, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        seed_requirement_templates(ProcessRequirementBuilder())

    def setUp(self):
        super().setUp()
        self.admin = get_user_model().objects.get(username="admin")
        self.idir_login_simulate(self.admin)
        self.service = BaseDashboardService()

    def _create_permit_with_module(self):
        """POST seeds the permit; the submission-date update attaches the
        process-requirement working copies as a module."""
        resp = self.client.post(
            reverse("permit_application_create"),
            data=json.dumps(create_payload()),
            content_type="application/json",
        )
        pk = resp.json()["resourceinstanceid"]
        self.client.patch(
            reverse("api_permit_application", args=[pk]),
            data=json.dumps(submission_payload()),
            content_type="application/json",
        )
        return pk

    def _permit(self, pk):
        """The permit tree loaded with the module nodes, the way the dashboards
        load it before folding in module completion."""
        return ResourceTileTree.get_tiles(
            GraphSlugs.PERMIT_APPLICATION,
            resource_ids=[str(pk)],
            nodes=self.service.nodes(
                GraphSlugs.PERMIT_APPLICATION,
                [
                    pa.MODULE_ID,
                    pa.MODULE_NAME,
                    pa.MODULE_ORDER,
                    pa.MODULE_COMPLETED_DATE,
                    pa.IS_MODULE_COMPLETED,
                ],
            ),
            as_representation=True,
        ).get(pk=pk)

    def _module_tiles(self, pk):
        _, module_ng = node_info(GraphSlugs.PERMIT_APPLICATION, pa.IS_MODULE_COMPLETED)
        return list(
            TileModel.objects.filter(resourceinstance_id=pk, nodegroup_id=module_ng)
        )

    def _mark_completed(self, tile):
        node_id, _ = node_info(GraphSlugs.PERMIT_APPLICATION, pa.IS_MODULE_COMPLETED)
        tile.data[node_id] = True
        tile.save()

    def test_reports_counts_and_the_outstanding_module(self):
        pk = self._create_permit_with_module()
        module_tiles = self._module_tiles(pk)
        self.assertTrue(module_tiles, "fixture should attach a module")

        # Not completed yet: it is the module the permit is waiting on.
        progress = self.service._module_progress(self._permit(pk))
        self.assertEqual(progress.total, 1)
        self.assertEqual(progress.completed, 0)
        self.assertTrue(progress.current_module)

        # Mark it complete; nothing is outstanding and the count moves.
        self._mark_completed(module_tiles[0])
        progress = self.service._module_progress(self._permit(pk))
        self.assertEqual(progress.completed, 1)
        self.assertEqual(progress.current_module, "")

    def test_no_modules_reports_zero(self):
        plain = ResourceTileTree.get_tiles(
            GraphSlugs.PERMIT_APPLICATION,
            nodes=self.service.nodes(GraphSlugs.PERMIT_APPLICATION, [pa.MODULE_NAME]),
            as_representation=True,
        ).none()
        self.assertEqual(
            [
                (p.total, p.completed, p.current_module)
                for p in (self.service._module_progress(x) for x in plain)
            ],
            [],
        )
