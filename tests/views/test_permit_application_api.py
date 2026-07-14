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
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.util.aliases.permit_application import (
    PermitApplicationAliases as aliases,
    PermitApplicationGroupAliases as group_aliases,
)
from arches_controlled_lists.models import ListItem

from arches.app.models.models import TileModel

from bcap.util.bcap_aliases import ALIASED_DATA, GraphSlugs
from bcap.util.graph import get_node, node_id
from bcap.builders.process_requirement_builder import ProcessRequirementBuilder
from bcap.util.i18n import localized_string

from tests.permit_fixtures import seed_requirement_templates
from tests.views.helpers import AuthTestHelper


def _api_reference_value(slug, alias, label=None):
    """Build a reference value in the format the REST serializer expects.

    The builder's ``reference_value()`` returns bare UUID strings, which are
    correct for tile saves but are rejected by the DRF serializer's
    ``ReferenceDataType.to_python``, which requires dicts with ``uri``,
    ``labels``, and ``list_id`` keys."""
    node = get_node(slug, alias)
    list_id = node.config["controlledList"]
    qs = ListItem.objects.filter(list_id=list_id)
    item = (
        qs.filter(list_item_values__value=label).first()
        if label
        else qs.order_by("sortorder").first()
    )
    labels = [
        {
            "id": str(lv.pk),
            "value": lv.value,
            "language_id": lv.language_id,
            "valuetype_id": lv.valuetype_id,
            "list_item_id": str(item.pk),
        }
        for lv in item.list_item_values.all()
    ]
    return [{"uri": item.uri, "labels": labels, "list_id": str(list_id)}]


def create_payload():
    """A create body: the identification tile the seeded id shares with the
    required project_name."""
    return {
        ALIASED_DATA: {
            group_aliases.APPLICATION_IDENTIFICATION: {
                ALIASED_DATA: {
                    aliases.PROJECT_NAME: "Test Project",
                    "filing_type": _api_reference_value(
                        "permit_application", "filing_type"
                    ),
                }
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
        seed_requirement_templates(ProcessRequirementBuilder())

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
        if not admin:
            return []
        return [
            requirement
            for module in (admin.aliased_data.process_module or [])
            for requirement in (module.aliased_data.process_requirement or [])
        ]

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

    def test_submission_stamps_module_and_requirement_ids(self):
        # The assign-module-ids hook mints the module id on save and stamps each
        # requirement id from it in post_save.
        pk = self._create()
        self._patch(pk, submission_payload())

        admin = self._permit(pk).aliased_data.application_admin
        module = (admin.aliased_data.process_module or [])[0]
        module_id = module.aliased_data.module_id
        self.assertRegex(module_id, r"^PERMIT-APPLICATION-\d+$")

        identifications = [
            localized_string(
                requirement.aliased_data.requirement_identification.aliased_data.requirement_identification
            )
            for requirement in ResourceTileTree.get_tiles(
                GraphSlugs.PROCESS_REQUIREMENT
            ).filter(is_template_requirement=False)
        ]
        derived = [i for i in identifications if i.startswith(f"{module_id}-")]
        self.assertEqual(len(derived), 3)
        for identification in derived:
            self.assertRegex(identification, r"-\d{3}$")

    def _non_template_requirement_count(self):
        return (
            ResourceTileTree.get_tiles(GraphSlugs.PROCESS_REQUIREMENT)
            .filter(is_template_requirement=False)
            .count()
        )

    def test_remove_module_deletes_tile_and_working_copies(self):
        pk = self._create()
        self._patch(pk, submission_payload())
        module = (
            self._permit(pk).aliased_data.application_admin.aliased_data.process_module
            or []
        )[0]
        # The default module's grouping parent plus its three requirements.
        self.assertEqual(self._non_template_requirement_count(), 4)

        ProcessRequirementService(
            user=get_user_model().objects.get(username="admin")
        ).remove_module(pk, module.tileid)

        admin = self._permit(pk).aliased_data.application_admin
        self.assertEqual(admin.aliased_data.process_module or [], [])
        self.assertEqual(self._non_template_requirement_count(), 0)

    def test_remove_module_ignores_a_tile_from_another_permit(self):
        pk = self._create()
        self._patch(pk, submission_payload())
        other = self._create()
        self._patch(other, submission_payload())
        module = (
            self._permit(
                other
            ).aliased_data.application_admin.aliased_data.process_module
            or []
        )[0]

        # The module tile belongs to `other`, so removing it against `pk` is a
        # no-op: neither permit's module is touched.
        ProcessRequirementService().remove_module(pk, module.tileid)

        self.assertEqual(len(self._requirements(pk)), 3)
        self.assertEqual(len(self._requirements(other)), 3)

    def _module_tileid(self, pk):
        admin = self._permit(pk).aliased_data.application_admin
        return (admin.aliased_data.process_module or [])[0].tileid

    def _ordered_requirement_ids(self, module_tileid):
        ref = node_id(GraphSlugs.PERMIT_APPLICATION, aliases.PROCESS_REQUIREMENT)
        order = node_id(
            GraphSlugs.PERMIT_APPLICATION, aliases.PROCESS_REQUIREMENT_ORDER
        )
        rows = []
        for child in TileModel.objects.filter(parenttile_id=module_tileid):
            references = child.data.get(ref) or []
            if references:
                rows.append(
                    (int(child.data.get(order) or 0), references[0]["resourceId"])
                )
        return [rid for _, rid in sorted(rows)]

    def test_reorder_requirements_renumbers_children(self):
        pk = self._create()
        self._patch(pk, submission_payload())
        module_tileid = self._module_tileid(pk)
        ids = self._ordered_requirement_ids(module_tileid)
        self.assertEqual(len(ids), 3)

        reversed_ids = list(reversed(ids))
        ProcessRequirementService().reorder_requirements(
            pk, module_tileid, reversed_ids
        )
        self.assertEqual(self._ordered_requirement_ids(module_tileid), reversed_ids)

    def test_remove_requirement_deletes_child_and_resource_only(self):
        pk = self._create()
        self._patch(pk, submission_payload())
        module_tileid = self._module_tileid(pk)
        target = self._ordered_requirement_ids(module_tileid)[0]

        ProcessRequirementService().remove_requirement(pk, module_tileid, target)

        remaining = self._ordered_requirement_ids(module_tileid)
        self.assertEqual(len(remaining), 2)
        self.assertNotIn(target, remaining)
        self.assertFalse(ResourceTileTree.objects.filter(pk=target).exists())
        # Grouping parent stays (shared): parent + 2 remaining = 3 non-templates.
        self.assertEqual(self._non_template_requirement_count(), 3)

    def test_add_blank_requirement_appends_to_module(self):
        pk = self._create()
        self._patch(pk, submission_payload())
        module_tileid = self._module_tileid(pk)
        before = self._ordered_requirement_ids(module_tileid)
        self.assertEqual(len(before), 3)

        ProcessRequirementService().add_blank_requirement(
            pk, module_tileid, "Custom step"
        )

        after = self._ordered_requirement_ids(module_tileid)
        self.assertEqual(len(after), 4)
        new_ids = set(after) - set(before)
        self.assertEqual(len(new_ids), 1)
        # Appended last, after the existing requirements.
        self.assertEqual(after[-1], next(iter(new_ids)))

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

    def test_inject_requirements_builds_every_admin_nesting(self):
        group = group_aliases.APPLICATION_ADMIN
        for body in self._nesting_variants(group):
            with self.subTest(body=body):
                service = PermitApplicationService()
                _parent, copies = service._inject_requirements_from_templates(body)
                admin = body[ALIASED_DATA][group][ALIASED_DATA]
                module = admin[group_aliases.PROCESS_MODULE][0][ALIASED_DATA]
                self.assertEqual(len(module[aliases.PROCESS_REQUIREMENT]), len(copies))
