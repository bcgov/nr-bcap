"""Reimport the permit resource models, the controlled lists their SKOS files
define, and the process-requirement templates, so a dev database matches what is
checked in."""

from pathlib import Path

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand

from arches.app.models.resource import Resource
from arches.management.commands.packages import Command as PackagesCommand
from arches_controlled_lists.utils.skos import SKOSReader

from bcap.management.commands.seed_template_requirements import (
    Command as SeedTemplatesCommand,
)
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)

BRANCHES = [
    "Material Collection",
    "Methodology",
    "Recordings",
    "Requirement Checklist",
]

RESOURCE_MODELS = [
    "Alteration",
    "BCAP Message",
    "Document Submission",
    "Inspection",
    "Investigation",
    "Notice of Project Intent",
    "Permit Application",
    "Process Requirement",
    "Workflow Drafts",
]


def _pkg():
    return Path(apps.get_app_config("bcap").path) / "pkg"


class Command(BaseCommand):
    help = (
        "Reimport the permit resource models, the SKOS controlled lists, and the "
        "process-requirement templates from the checked-in package files."
    )

    def add_arguments(self, parser):
        parser.add_argument("--skip-graphs", action="store_true")
        parser.add_argument(
            "--skip-lists",
            action="store_true",
            help="Leave controlled lists alone instead of replacing them from SKOS.",
        )
        parser.add_argument(
            "--skip-requirements",
            action="store_true",
            help="Leave the process-requirement templates alone.",
        )

    def handle(self, *args, **options):
        if not options["skip_graphs"]:
            self.reload_graphs()
        if not options["skip_lists"]:
            self.reload_lists()
        if not options["skip_requirements"]:
            self.reload_requirement_templates()

    def reload_graphs(self):
        branches = self._graph_paths("branches", BRANCHES)
        models = self._graph_paths("resource_models", RESOURCE_MODELS)
        PackagesCommand().import_graphs(branches + models)
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(branches)} branches and {len(models)} resource models."
            )
        )

    @staticmethod
    def _graph_paths(subdir, names):
        paths = []
        for name in names:
            path = _pkg() / "graphs" / subdir / f"{name}.json"
            if not path.exists():
                raise FileNotFoundError(f"No graph file for '{name}'.")
            paths.append(str(path))
        return paths

    def reload_lists(self):
        # Item ids are uuidv5s of their SKOS subject, so overwriting rebuilds the
        # same ids and leaves tiles that reference them intact.
        for path in sorted((_pkg() / "reference_data" / "skos").glob("*.xml")):
            reader = SKOSReader()
            reader.save_controlled_lists_from_skos(
                reader.read_file(str(path)), overwrite_options="overwrite"
            )
            self.stdout.write(self.style.SUCCESS(f"Loaded controlled list {path.name}"))

    def reload_requirement_templates(self):
        for template in ProcessRequirementService()._templates_by_id().values():
            Resource.objects.get(pk=template.pk).delete()
        call_command("seed_template_requirements")
        if not SeedTemplatesCommand._templates_exist():
            raise RuntimeError("Requirement templates missing after reseed.")
