"""End-to-end tests for the Permit Application endpoints: POST creates an
application and seeds its id; the update that first sets the submission date
attaches the process-requirement working copies."""

import json
from types import SimpleNamespace
from unittest import mock

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
from bcap.services.process_requirement.template_specs import load
from bcap.util.i18n import localized_string

from tests.permit_fixtures import seed_requirement_templates
from tests.views.helpers import AuthTestHelper, login_as

# The permit module's child requirements, seeded by migration from the spec.
PERMIT_REQUIREMENTS = len(load("permit")["requirements"])


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
        cls.submitted_pk = cls._build_submitted_permit()
        cls.other_submitted_pk = cls._build_submitted_permit()
        (
            cls.investigation_pk,
            cls.investigation_host,
            cls.investigation_requirements,
        ) = cls._build_permit_with_investigation()

    @classmethod
    def _build_permit_with_investigation(cls):
        """A permit with an investigation module attached, the way the
        module-host submission does. Shared for the same reason as the
        submitted permit: several tests need exactly this and nothing more."""
        pk = cls._create_permit(cls._logged_in_client())
        host = ProcessRequirementBuilder().make_resource(GraphSlugs.INVESTIGATION)
        service = ProcessRequirementService(
            user=get_user_model().objects.get(username="admin")
        )
        return pk, host, service.attach_requirements(pk, "investigation", host)

    @classmethod
    def _logged_in_client(cls):
        client = cls.client_class()
        login_as(client, get_user_model().objects.get(username="admin"))
        return client

    @classmethod
    def _create_permit(cls, client):
        resp = client.post(
            reverse("permit_application_create"),
            data=json.dumps(create_payload()),
            content_type="application/json",
        )
        return resp.json()["resourceinstanceid"]

    @classmethod
    def _build_submitted_permit(cls):
        """A permit past its submission date, with its requirements attached.

        Building it costs a create plus a submit (~3s), which most tests here
        need identically, so it is built once for the class instead of per test.
        Each test still runs in its own transaction, so mutations roll back."""
        client = cls._logged_in_client()
        pk = cls._create_permit(client)
        client.patch(
            reverse("api_permit_application", args=[pk]),
            data=json.dumps(submission_payload()),
            content_type="application/json",
        )
        return pk

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
        draft = self._create()
        self.assertRegex(self._application_id(draft), r"^APP-\d+$")
        # The class-level permits came through the same endpoint, so the ids
        # the seeder mints have to differ from theirs.
        self.assertNotEqual(
            self._application_id(draft), self._application_id(self.submitted_pk)
        )
        self.assertEqual(self._requirements(draft), [])

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
        self.assertEqual(
            len(self._requirements(resp.json()["resourceinstanceid"])),
            PERMIT_REQUIREMENTS,
        )

    def test_submission_via_put_attaches_requirements(self):
        pk = self._create()
        # Round-trip the resource (so tile ids are preserved), set the date,
        # and PUT it back.
        body = self._get(pk)
        body[ALIASED_DATA][group_aliases.APPLICATION_ADMIN] = {
            ALIASED_DATA: {aliases.APPLICATION_SUBMISSION_DATE: "2026-06-18"}
        }
        self.assertEqual(self._put(pk, body).status_code, 200)
        self.assertEqual(len(self._requirements(pk)), PERMIT_REQUIREMENTS)

    def test_submission_stamps_module_and_requirement_ids(self):
        # The assign-module-ids hook mints the module id on save and stamps each
        # requirement id from it in post_save.
        pk = self.submitted_pk

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
        self.assertEqual(len(derived), PERMIT_REQUIREMENTS)
        for identification in derived:
            self.assertRegex(identification, r"-\d{3}$")

    def _non_template_requirement_count(self):
        return (
            ResourceTileTree.get_tiles(GraphSlugs.PROCESS_REQUIREMENT)
            .filter(is_template_requirement=False)
            .count()
        )

    def test_remove_module_deletes_tile_and_working_copies(self):
        pk = self.submitted_pk
        module = (
            self._permit(pk).aliased_data.application_admin.aliased_data.process_module
            or []
        )[0]
        before = self._non_template_requirement_count()

        ProcessRequirementService(
            user=get_user_model().objects.get(username="admin")
        ).remove_module(pk, module.tileid)

        admin = self._permit(pk).aliased_data.application_admin
        self.assertEqual(admin.aliased_data.process_module or [], [])
        # The module's requirements plus its grouping parent are gone.
        self.assertEqual(
            before - self._non_template_requirement_count(), PERMIT_REQUIREMENTS + 1
        )

    def test_remove_module_ignores_a_tile_from_another_permit(self):
        pk = self.submitted_pk
        other = self.other_submitted_pk
        module = (
            self._permit(
                other
            ).aliased_data.application_admin.aliased_data.process_module
            or []
        )[0]

        # The module tile belongs to `other`, so removing it against `pk` is a
        # no-op: neither permit's module is touched.
        ProcessRequirementService().remove_module(pk, module.tileid)

        self.assertEqual(len(self._requirements(pk)), PERMIT_REQUIREMENTS)
        self.assertEqual(len(self._requirements(other)), PERMIT_REQUIREMENTS)

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
        pk = self.submitted_pk
        module_tileid = self._module_tileid(pk)
        ids = self._ordered_requirement_ids(module_tileid)
        self.assertEqual(len(ids), PERMIT_REQUIREMENTS)

        reversed_ids = list(reversed(ids))
        ProcessRequirementService().reorder_requirements(
            pk, module_tileid, reversed_ids
        )
        self.assertEqual(self._ordered_requirement_ids(module_tileid), reversed_ids)

    def test_remove_requirement_deletes_child_and_resource_only(self):
        pk = self.submitted_pk
        module_tileid = self._module_tileid(pk)
        target = self._ordered_requirement_ids(module_tileid)[0]
        before = self._non_template_requirement_count()

        ProcessRequirementService().remove_requirement(pk, module_tileid, target)

        remaining = self._ordered_requirement_ids(module_tileid)
        self.assertEqual(len(remaining), PERMIT_REQUIREMENTS - 1)
        self.assertNotIn(target, remaining)
        self.assertFalse(ResourceTileTree.objects.filter(pk=target).exists())
        # Only the target goes: the grouping parent stays (shared), as does the
        # permit hosting its own submission.
        self.assertEqual(before - self._non_template_requirement_count(), 1)

    def test_add_blank_requirement_appends_to_module(self):
        pk = self.submitted_pk
        module_tileid = self._module_tileid(pk)
        before = self._ordered_requirement_ids(module_tileid)
        self.assertEqual(len(before), PERMIT_REQUIREMENTS)

        ProcessRequirementService().add_blank_requirement(
            pk, module_tileid, "Custom step"
        )

        after = self._ordered_requirement_ids(module_tileid)
        self.assertEqual(len(after), PERMIT_REQUIREMENTS + 1)
        new_ids = set(after) - set(before)
        self.assertEqual(len(new_ids), 1)
        # Appended last, after the existing requirements.
        self.assertEqual(after[-1], next(iter(new_ids)))

    def test_resubmission_does_not_reattach_requirements(self):
        pk = self.submitted_pk
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
                cloned = service._inject_requirements_from_templates(body)
                admin = body[ALIASED_DATA][group][ALIASED_DATA]
                module = admin[group_aliases.PROCESS_MODULE][0][ALIASED_DATA]
                self.assertEqual(
                    len(module[aliases.PROCESS_REQUIREMENT]), len(cloned.requirements)
                )
                # The permit's own-submission requirement is held back for the
                # caller to link once the permit itself is saved.
                self.assertIsNotNone(cloned.self_hosted)

    # HTTP-level coverage for the module and checklist endpoints. The tests above
    # drive the service directly; these go through the DRF views and the request
    # serializers so the serializers and view wiring are exercised too.
    def _reorder(self, pk, module_tileid, order):
        return self.client.patch(
            reverse("module_requirements", args=[pk, module_tileid]),
            data=json.dumps({"order": order}),
            content_type="application/json",
        )

    def _add_requirement(self, pk, module_tileid, name=None):
        return self.client.post(
            reverse("module_requirements", args=[pk, module_tileid]),
            data=json.dumps({} if name is None else {"name": name}),
            content_type="application/json",
        )

    def _delete_requirement(self, pk, module_tileid, requirement_id):
        return self.client.delete(
            reverse("module_requirement", args=[pk, module_tileid, requirement_id])
        )

    def _delete_module(self, pk, module_tileid):
        return self.client.delete(reverse("permit_module", args=[pk, module_tileid]))

    def _patch_checklist(self, requirement_id, body):
        return self.client.patch(
            reverse("requirement_checklist", args=[requirement_id]),
            data=json.dumps(body),
            content_type="application/json",
        )

    def test_reorder_endpoint_renumbers_children(self):
        pk = self.submitted_pk
        module_tileid = self._module_tileid(pk)
        reversed_ids = list(reversed(self._ordered_requirement_ids(module_tileid)))

        resp = self._reorder(pk, module_tileid, reversed_ids)

        self.assertEqual(resp.status_code, 204)
        self.assertEqual(self._ordered_requirement_ids(module_tileid), reversed_ids)

    def test_reorder_endpoint_rejects_a_non_uuid_order_entry(self):
        # The reorder serializer requires the order entries to be UUIDs.
        pk = self.submitted_pk
        module_tileid = self._module_tileid(pk)

        resp = self._reorder(pk, module_tileid, ["not-a-uuid"])

        self.assertEqual(resp.status_code, 400)

    def test_add_requirement_endpoint_appends_named_requirement(self):
        pk = self.submitted_pk
        module_tileid = self._module_tileid(pk)
        before = self._ordered_requirement_ids(module_tileid)

        resp = self._add_requirement(pk, module_tileid, "Custom step")

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(
            len(self._ordered_requirement_ids(module_tileid)), len(before) + 1
        )

    def test_add_requirement_endpoint_defaults_the_name(self):
        # The add serializer makes name optional; the view supplies a default.
        pk = self.submitted_pk
        module_tileid = self._module_tileid(pk)

        resp = self._add_requirement(pk, module_tileid)

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(
            len(self._ordered_requirement_ids(module_tileid)), PERMIT_REQUIREMENTS + 1
        )

    def test_delete_requirement_endpoint_removes_child(self):
        pk = self.submitted_pk
        module_tileid = self._module_tileid(pk)
        target = self._ordered_requirement_ids(module_tileid)[0]

        resp = self._delete_requirement(pk, module_tileid, target)

        self.assertEqual(resp.status_code, 204)
        self.assertNotIn(target, self._ordered_requirement_ids(module_tileid))

    def test_delete_module_endpoint_removes_the_tile(self):
        pk = self.submitted_pk
        module_tileid = self._module_tileid(pk)

        resp = self._delete_module(pk, module_tileid)

        self.assertEqual(resp.status_code, 204)
        admin = self._permit(pk).aliased_data.application_admin
        self.assertEqual(admin.aliased_data.process_module or [], [])

    def test_checklist_endpoint_saves_name_and_steps(self):
        requirement = ProcessRequirementBuilder().make_blank_checklist_requirement(
            "Draft"
        )

        resp = self._patch_checklist(
            str(requirement.pk),
            {
                "name": "Checklist",
                "steps": [
                    {"name": "First", "description": "one"},
                    {"name": "Second", "description": "two"},
                ],
            },
        )

        self.assertEqual(resp.status_code, 204)

    def test_checklist_endpoint_unknown_requirement_returns_404(self):
        resp = self._patch_checklist(
            "00000000-0000-0000-0000-000000000000",
            {"name": "x", "steps": []},
        )
        self.assertEqual(resp.status_code, 404)

    def test_module_host_endpoint_unknown_type_returns_400(self):
        # A permit type with no host graph is rejected before the serializer.
        pk = self._create()
        resp = self.client.get(
            reverse("seed_process_requirements", args=[pk, "not_a_module"])
        )
        self.assertEqual(resp.status_code, 400)

    def test_module_host_endpoint_unknown_permit_returns_404(self):
        resp = self.client.get(
            reverse(
                "seed_process_requirements",
                args=["00000000-0000-0000-0000-000000000000", "investigation"],
            )
        )
        self.assertEqual(resp.status_code, 404)

    def test_attach_requirements_adds_investigation_module(self):
        pk = self.investigation_pk

        self.assertTrue(self.investigation_requirements)
        admin = self._permit(pk).aliased_data.application_admin
        names = [
            localized_string(module.aliased_data.module_name)
            for module in (admin.aliased_data.process_module or [])
        ]
        self.assertIn("Investigation", names)

    def test_permit_module_tiles_lists_the_attached_host(self):
        service = ProcessRequirementService(
            user=get_user_model().objects.get(username="admin")
        )
        hosts = service.permit_module_tiles(self.investigation_pk, "investigation")

        self.assertIn(str(self.investigation_host.pk), [str(h.pk) for h in hosts])

    def test_permit_module_tiles_is_empty_before_submission(self):
        # The permit module hosts itself, but nothing is attached until the
        # submission date is set.
        service = ProcessRequirementService()
        self.assertEqual(service.permit_module_tiles(self._create(), "permit"), [])

    def test_submission_links_the_permit_as_its_own_host(self):
        # The permit module's own-submission requirement points back at the
        # permit, linked after the save because the id exists only then.
        pk = self.submitted_pk

        hosts = ProcessRequirementService().permit_module_tiles(pk, "permit")
        self.assertEqual([str(host.pk) for host in hosts], [str(pk)])

    def test_module_host_endpoint_lists_attached_hosts(self):
        resp = self.client.get(
            reverse(
                "seed_process_requirements",
                args=[self.investigation_pk, "investigation"],
            )
        )

        self.assertEqual(resp.status_code, 200)
        ids = [host.get("resourceinstanceid") for host in resp.json()]
        self.assertIn(str(self.investigation_host.pk), ids)

    def test_permit_module_tiles_empty_when_module_has_no_hosts(self):
        # The default module has requirements but no host resources, so an
        # investigation-host lookup finds no hosts.
        pk = self.submitted_pk

        service = ProcessRequirementService()
        self.assertEqual(list(service.permit_module_tiles(pk, "investigation")), [])

    def test_reorder_ignores_a_module_from_another_permit(self):
        pk = self.submitted_pk
        other_module = self._module_tileid(self.other_submitted_pk)
        before = self._ordered_requirement_ids(other_module)

        # Reordering `other`'s module against `pk` is rejected as a no-op.
        ProcessRequirementService().reorder_requirements(
            pk, other_module, list(reversed(before))
        )

        self.assertEqual(self._ordered_requirement_ids(other_module), before)

    def test_reorder_with_empty_order_leaves_children_untouched(self):
        pk = self.submitted_pk
        module_tileid = self._module_tileid(pk)
        before = self._ordered_requirement_ids(module_tileid)

        # No id maps to a position, so every child is skipped.
        ProcessRequirementService().reorder_requirements(pk, module_tileid, [])

        self.assertEqual(self._ordered_requirement_ids(module_tileid), before)

    def test_remove_requirement_unknown_id_is_a_noop(self):
        pk = self.submitted_pk
        module_tileid = self._module_tileid(pk)
        before = len(self._ordered_requirement_ids(module_tileid))

        ProcessRequirementService().remove_requirement(
            pk, module_tileid, "00000000-0000-0000-0000-000000000000"
        )

        self.assertEqual(len(self._ordered_requirement_ids(module_tileid)), before)

    def test_add_blank_requirement_unknown_module_returns_none(self):
        pk = self.submitted_pk

        result = ProcessRequirementService().add_blank_requirement(
            pk, "00000000-0000-0000-0000-000000000000", "x"
        )

        self.assertIsNone(result)

    def test_removing_the_permit_module_leaves_the_permit_itself_alive(self):
        # The permit hosts the module's own submission, so it lands in the
        # delete set until the guard discards it.
        pk = self.submitted_pk
        module_tileid = self._module_tileid(pk)
        self_hosted = self._ordered_requirement_ids(module_tileid)[0]

        ProcessRequirementService().remove_requirement(pk, module_tileid, self_hosted)
        self.assertTrue(ResourceTileTree.objects.filter(pk=pk).exists())

        ProcessRequirementService().remove_module(pk, module_tileid)
        self.assertTrue(ResourceTileTree.objects.filter(pk=pk).exists())

    def test_saved_id_reads_the_create_response_or_none(self):
        read = PermitApplicationService._saved_id
        self.assertEqual(
            read(SimpleNamespace(data={"resourceinstanceid": "abc"})), "abc"
        )
        # A response with no body, or one carrying no id, yields None.
        self.assertIsNone(read(SimpleNamespace(data=None)))
        self.assertIsNone(read(SimpleNamespace(data={})))
        self.assertIsNone(read(SimpleNamespace()))

    def test_a_permit_id_of_none_leaves_the_module_unlinked(self):
        # What a create response carrying no id leads to: the link is skipped
        # rather than raising, so the requirement is silently left unhosted.
        requirements = ProcessRequirementService()
        cloned = requirements._clone_module("permit")
        self.assertIsNotNone(cloned.self_hosted)

        PermitApplicationService()._link_permit_to_itself(cloned, None)

        hosts = requirements.host_ids_by_requirement({str(cloned.self_hosted.pk)})
        self.assertFalse(hosts.get(str(cloned.self_hosted.pk)))

    def test_a_failed_link_rolls_the_clones_back_after_the_save(self):
        # The link runs after the permit is saved, so a failure there still
        # deletes every clone; the permit itself is already committed.
        pk = self._create()
        before = self._requirement_count()

        with mock.patch.object(
            ProcessRequirementService,
            "link_submission",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                PermitApplicationService().submit(
                    self._permit(pk), submission_payload(), lambda: None
                )

        self.assertEqual(self._requirement_count(), before)
        self.assertTrue(ResourceTileTree.objects.filter(pk=pk).exists())
