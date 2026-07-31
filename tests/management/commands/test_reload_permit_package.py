"""reload_permit_package reimports the checked-in package files. Only the
requirement-template reload is exercised here: reload_lists overwrites the
controlled lists from SKOS, which would rewrite the test database's lists, and
reload_graphs reimports every resource model."""

from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from bcap.management.commands.reload_permit_package import Command
from bcap.management.commands.seed_template_requirements import (
    Command as SeedTemplatesCommand,
)
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)


def _template_ids():
    return set(ProcessRequirementService()._templates_by_id())


class ReloadRequirementTemplatesTests(TestCase):
    def test_reseeds_the_templates_it_deleted(self):
        # The templates are seeded by migration, so they exist up front; the
        # command drops them all and seeds a fresh set with the same spec ids.
        before = _template_ids()
        self.assertTrue(before)

        call_command("reload_permit_package", "--skip-graphs", "--skip-lists")

        self.assertEqual(_template_ids(), before)

    def test_raises_when_the_reseed_leaves_no_templates(self):
        # The guard is what turns a silently-empty reseed into a loud failure.
        with mock.patch.object(
            SeedTemplatesCommand, "_templates_exist", return_value=False
        ):
            with self.assertRaises(RuntimeError):
                call_command("reload_permit_package", "--skip-graphs", "--skip-lists")

    def test_skipping_every_step_touches_nothing(self):
        before = _template_ids()

        call_command(
            "reload_permit_package",
            "--skip-graphs",
            "--skip-lists",
            "--skip-requirements",
        )

        self.assertEqual(_template_ids(), before)


class GraphPathTests(TestCase):
    """The graph reload resolves each name to a checked-in file up front, so a
    missing one fails before any import runs."""

    def test_every_named_graph_file_exists(self):
        self.assertTrue(Command._graph_paths("resource_models", ["Permit Application"]))

    def test_a_missing_graph_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            Command._graph_paths("resource_models", ["No Such Graph"])
