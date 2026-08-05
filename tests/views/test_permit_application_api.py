"""End-to-end tests for the Permit Application endpoints: POST creates an
application and seeds its id; the update that first sets the submission date
attaches the process-requirement working copies."""

import json
from types import SimpleNamespace
from unittest import mock
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from arches_querysets.models import ResourceTileTree

from bcap.services.dashboard.base_graph_service import BaseGraphService
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

from arches.app.models.models import ResourceInstance, TileModel

from bcap.util.bcap_aliases import ALIASED_DATA, GraphSlugs
from bcap.util.controlled_list import reference_value
from bcap.util.graph import get_node, node_id
from bcap.util.tiles import resource_instance_id, resource_instance_value
from bcap.builders.contributor_builder import ContributorSpec
from bcap.builders.process_requirement_builder import ProcessRequirementBuilder
from bcap.services.contributor.organization_service import OrganizationService
from bcap.services.process_requirement.template_specs import load
from bcap.util.i18n import localized_string
from bcap.views.organization_helpers import block_organization

from tests.builders import FixtureBuilder
from tests.controlled_list_fixtures import ControlledListFixtures
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
        (
            cls.draft_pk,
            cls.investigation_host,
            cls.investigation_requirements,
        ) = cls._build_permit_with_investigation()

    @classmethod
    def _build_permit_with_investigation(cls):
        """A permit with an investigation module attached, the way the
        module-host submission does. Never submitted, so it doubles as the
        draft for tests that just need an unsubmitted permit to read."""
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

    def _permit(self, pk, *node_aliases):
        """The permit tree, narrowed to the given node aliases. Hydrating every
        node of this graph is the most expensive thing these tests do, so pass
        the ones being read; no aliases means the whole tree (what the save path
        needs)."""
        nodes = (
            BaseGraphService.nodes(GraphSlugs.PERMIT_APPLICATION, node_aliases)
            if node_aliases
            else None
        )
        return ResourceTileTree.get_tiles(
            GraphSlugs.PERMIT_APPLICATION, resource_ids=[pk], nodes=nodes
        ).get()

    def _requirements(self, pk):
        admin = self._permit(
            pk, aliases.PROCESS_REQUIREMENT
        ).aliased_data.application_admin
        if not admin:
            return []
        return [
            requirement
            for module in (admin.aliased_data.process_module or [])
            for requirement in (module.aliased_data.process_requirement or [])
        ]

    def _application_id(self, pk):
        ident = self._permit(
            pk, aliases.APPLICATION_ID
        ).aliased_data.application_identification
        return localized_string(ident.aliased_data.application_id) if ident else ""

    def _requirement_count(self):
        return ResourceInstance.objects.filter(
            graph__slug=GraphSlugs.PROCESS_REQUIREMENT
        ).count()

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
        page = InternalDashboardService().get_cards(DashboardFilter())
        self.assertNotIn(self.draft_pk, [card.id for card in page.results])

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

    def test_put_and_delete_are_not_allowed(self):
        # A whole-resource replace would reset every node the body omits, the
        # owning organization included. Submission goes through PATCH, and
        # nothing deletes a permit through the API.
        pk = self.draft_pk

        self.assertEqual(self._put(pk, self._get(pk)).status_code, 405)
        self.assertEqual(
            self.client.delete(
                reverse("api_permit_application", args=[pk])
            ).status_code,
            405,
        )

    def test_submission_stamps_module_and_requirement_ids(self):
        # The assign-module-ids hook mints the module id on save and stamps each
        # requirement id from it in post_save.
        pk = self.submitted_pk

        admin = self._permit(pk, aliases.MODULE_ID).aliased_data.application_admin
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
            ResourceTileTree.get_tiles(
                GraphSlugs.PROCESS_REQUIREMENT,
                nodes=BaseGraphService.nodes(
                    GraphSlugs.PROCESS_REQUIREMENT, ["is_template_requirement"]
                ),
            )
            .filter(is_template_requirement=False)
            .count()
        )

    def test_remove_module_deletes_tile_and_working_copies(self):
        pk = self.submitted_pk
        module = self._module_tile(pk)
        before = self._non_template_requirement_count()

        ProcessRequirementService(
            user=get_user_model().objects.get(username="admin")
        ).remove_module(pk, module.tileid)

        admin = self._permit(pk, aliases.MODULE_NAME).aliased_data.application_admin
        self.assertEqual(admin.aliased_data.process_module or [], [])
        # The module's requirements plus its grouping parent are gone.
        self.assertEqual(
            before - self._non_template_requirement_count(), PERMIT_REQUIREMENTS + 1
        )

    def test_remove_module_ignores_a_tile_from_another_permit(self):
        pk = self.submitted_pk
        other = self.draft_pk
        module = self._module_tile(other)

        # The module tile belongs to `other`, so removing it against `pk` is a
        # no-op: neither permit's module is touched.
        ProcessRequirementService().remove_module(pk, module.tileid)

        self.assertEqual(len(self._requirements(pk)), PERMIT_REQUIREMENTS)
        self.assertEqual(self._module_tile(other).tileid, module.tileid)

    def _module_tile(self, pk):
        admin = self._permit(pk, aliases.MODULE_NAME).aliased_data.application_admin
        return (admin.aliased_data.process_module or [])[0]

    def _module_tileid(self, pk):
        return self._module_tile(pk).tileid

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
        pk = self.draft_pk
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

    def test_module_requirement_endpoints_reorder_add_and_delete(self):
        """One pass over the module-requirement endpoints. They share a permit
        and a module tile, and loading those per test cost more than the calls
        themselves."""
        pk = self.submitted_pk
        module_tileid = self._module_tileid(pk)
        before = self._ordered_requirement_ids(module_tileid)

        reversed_ids = list(reversed(before))
        self.assertEqual(
            self._reorder(pk, module_tileid, reversed_ids).status_code, 204
        )
        self.assertEqual(self._ordered_requirement_ids(module_tileid), reversed_ids)

        # The reorder serializer requires the order entries to be UUIDs.
        self.assertEqual(
            self._reorder(pk, module_tileid, ["not-a-uuid"]).status_code, 400
        )

        self.assertEqual(
            self._add_requirement(pk, module_tileid, "Custom step").status_code, 201
        )
        self.assertEqual(
            len(self._ordered_requirement_ids(module_tileid)), len(before) + 1
        )

        # The add serializer makes name optional; the view supplies a default.
        self.assertEqual(self._add_requirement(pk, module_tileid).status_code, 201)
        self.assertEqual(
            len(self._ordered_requirement_ids(module_tileid)), len(before) + 2
        )

        target = self._ordered_requirement_ids(module_tileid)[0]
        self.assertEqual(
            self._delete_requirement(pk, module_tileid, target).status_code, 204
        )
        self.assertNotIn(target, self._ordered_requirement_ids(module_tileid))

    def test_delete_module_endpoint_removes_the_tile(self):
        pk = self.submitted_pk
        module_tileid = self._module_tileid(pk)

        resp = self._delete_module(pk, module_tileid)

        self.assertEqual(resp.status_code, 204)
        admin = self._permit(pk, aliases.MODULE_NAME).aliased_data.application_admin
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

    def test_endpoints_reject_unknown_ids_and_types(self):
        unknown = "00000000-0000-0000-0000-000000000000"

        self.assertEqual(
            self._patch_checklist(unknown, {"name": "x", "steps": []}).status_code, 404
        )
        # A permit type with no host graph is rejected before the serializer.
        self.assertEqual(
            self.client.get(
                reverse(
                    "seed_process_requirements", args=[self.draft_pk, "not_a_module"]
                )
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.get(
                reverse("seed_process_requirements", args=[unknown, "investigation"])
            ).status_code,
            404,
        )

    def test_attached_investigation_module_and_its_host(self):
        """The attach puts an Investigation module on the permit, and both the
        service and the endpoint surface its host resource."""
        pk = self.draft_pk
        self.assertTrue(self.investigation_requirements)

        admin = self._permit(pk, aliases.MODULE_NAME).aliased_data.application_admin
        names = [
            localized_string(module.aliased_data.module_name)
            for module in (admin.aliased_data.process_module or [])
        ]
        self.assertIn("Investigation", names)

        service = ProcessRequirementService(
            user=get_user_model().objects.get(username="admin")
        )
        hosts = service.permit_module_tiles(pk, "investigation")
        self.assertIn(str(self.investigation_host.pk), [str(h.pk) for h in hosts])

        resp = self.client.get(
            reverse("seed_process_requirements", args=[pk, "investigation"])
        )
        self.assertEqual(resp.status_code, 200)
        ids = [host.get("resourceinstanceid") for host in resp.json()]
        self.assertIn(str(self.investigation_host.pk), ids)

    def test_permit_module_hosts_only_what_is_attached(self):
        """The permit module hosts the permit itself once submitted, and only
        then: a permit carrying no permit module has no hosts, and a module with
        requirements but no host resources has none for another type."""
        service = ProcessRequirementService()

        self.assertEqual(service.permit_module_tiles(self.draft_pk, "permit"), [])

        # The own-submission requirement points back at the permit, linked after
        # the save because the id exists only then.
        hosts = service.permit_module_tiles(self.submitted_pk, "permit")
        self.assertEqual([str(host.pk) for host in hosts], [str(self.submitted_pk)])

        self.assertEqual(
            list(service.permit_module_tiles(self.submitted_pk, "investigation")), []
        )

    def test_ids_that_dont_belong_to_the_permit_are_no_ops(self):
        """Another permit's module, an empty order, an unknown requirement and
        an unknown module all leave the permit's module exactly as it was."""
        unknown = "00000000-0000-0000-0000-000000000000"
        pk = self.submitted_pk
        module_tileid = self._module_tileid(pk)
        before = self._ordered_requirement_ids(module_tileid)
        service = ProcessRequirementService()

        other_module = self._module_tileid(self.draft_pk)
        other_before = self._ordered_requirement_ids(other_module)
        service.reorder_requirements(pk, other_module, list(reversed(other_before)))
        self.assertEqual(self._ordered_requirement_ids(other_module), other_before)

        # No id maps to a position, so every child is skipped.
        service.reorder_requirements(pk, module_tileid, [])
        self.assertEqual(self._ordered_requirement_ids(module_tileid), before)

        service.remove_requirement(pk, module_tileid, unknown)
        self.assertEqual(self._ordered_requirement_ids(module_tileid), before)

        self.assertIsNone(service.add_blank_requirement(pk, unknown, "x"))

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
        pk = self.draft_pk
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


@override_settings(ROOT_URLCONF="tests.test_urls")
class PermitApplicationOrganizationTests(AuthTestHelper, TestCase):
    """The owning-organization stamp: create records the creator's company, and
    only branch staff may set or move it on an update."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ControlledListFixtures.seed()
        cls.org = FixtureBuilder().make_contributor(
            ContributorSpec(
                reference_value("contributor", "contributor_type"), None, "Acme Corp"
            )
        )
        cls.org_id = str(cls.org.pk)

    def setUp(self):
        super().setUp()
        self.idir_login_simulate(get_user_model().objects.get(username="admin"))

    def _owning_organization(self, pk):
        node = node_id(GraphSlugs.PERMIT_APPLICATION, aliases.OWNING_ORGANIZATION)
        tile = TileModel.objects.filter(
            resourceinstance_id=pk, data__has_key=node
        ).first()
        return resource_instance_id(tile.data[node]) if tile else ""

    def _post_as_member_of(self, orgs, payload=None):
        with mock.patch.object(
            OrganizationService, "organization_ids", return_value=orgs
        ):
            return self.client.post(
                reverse("permit_application_create"),
                data=json.dumps(payload or create_payload()),
                content_type="application/json",
            )

    def test_create_stamps_the_creators_only_organization(self):
        resp = self._post_as_member_of({self.org_id})

        self.assertEqual(resp.status_code, 201)
        pk = resp.json()["resourceinstanceid"]
        self.assertEqual(self._owning_organization(pk), self.org_id)

    def test_a_member_of_no_organization_creates_an_unstamped_application(self):
        resp = self._post_as_member_of(set())

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(
            self._owning_organization(resp.json()["resourceinstanceid"]), ""
        )

    def test_a_member_of_several_organizations_has_to_pick_one(self):
        both = {self.org_id, str(uuid4())}

        resp = self._post_as_member_of(both)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("organization_id", resp.json())

        payload = {**create_payload(), "organization_id": self.org_id}
        self.assertEqual(self._post_as_member_of(both, payload).status_code, 201)

    def test_an_application_cannot_be_filed_under_someone_elses_organization(self):
        payload = {**create_payload(), "organization_id": self.org_id}

        self.assertEqual(self._post_as_member_of(set(), payload).status_code, 403)

    def test_an_external_update_cannot_move_the_application(self):
        # block_organization strips the node before the save ever sees it, so
        # the stamp an applicant sends on submission is simply dropped.
        body = {
            ALIASED_DATA: {
                group_aliases.APPLICATION_IDENTIFICATION: {
                    ALIASED_DATA: {
                        aliases.PROJECT_NAME: "Renamed",
                        aliases.OWNING_ORGANIZATION: resource_instance_value(
                            self.org_id
                        ),
                    }
                }
            }
        }
        request = SimpleNamespace(user=self.user, data=body)

        block_organization(
            request,
            group_aliases.APPLICATION_IDENTIFICATION,
            aliases.OWNING_ORGANIZATION,
        )

        identification = body[ALIASED_DATA][group_aliases.APPLICATION_IDENTIFICATION]
        self.assertNotIn(aliases.OWNING_ORGANIZATION, identification[ALIASED_DATA])
        self.assertEqual(identification[ALIASED_DATA][aliases.PROJECT_NAME], "Renamed")

    def test_branch_staff_keep_the_organization_they_send(self):
        admin = get_user_model().objects.get(username="admin")
        body = {
            ALIASED_DATA: {
                group_aliases.APPLICATION_IDENTIFICATION: {
                    ALIASED_DATA: {
                        aliases.OWNING_ORGANIZATION: resource_instance_value(
                            self.org_id
                        )
                    }
                }
            }
        }

        block_organization(
            SimpleNamespace(user=admin, data=body),
            group_aliases.APPLICATION_IDENTIFICATION,
            aliases.OWNING_ORGANIZATION,
        )

        identification = body[ALIASED_DATA][group_aliases.APPLICATION_IDENTIFICATION]
        self.assertIn(aliases.OWNING_ORGANIZATION, identification[ALIASED_DATA])

    def test_a_body_that_never_mentions_the_group_is_left_alone(self):
        body = {ALIASED_DATA: {}}

        block_organization(
            SimpleNamespace(user=self.user, data=body),
            group_aliases.APPLICATION_IDENTIFICATION,
            aliases.OWNING_ORGANIZATION,
        )

        self.assertEqual(body, {ALIASED_DATA: {}})
