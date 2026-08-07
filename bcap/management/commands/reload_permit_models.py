"""Reimport the permit resource models, the controlled lists their SKOS files
define, and the process-requirement templates, so a dev database matches what is
checked in."""

import json
from pathlib import Path

from django.apps import apps
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import BaseCommand

from arches.app.models import models as arches_models
from arches.app.models.graph import Graph
from arches.app.models.resource import Resource
from arches.management.commands.packages import Command as PackagesCommand
from arches_controlled_lists.utils.skos import SKOSReader

from bcap.management.commands.seed_template_requirements import templates_exist
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)

BRANCHES = [
    "Material Collection",
    "Methodology",
    "Recordings",
    "Requirement Checklist",
]

# Resource models that are NOT part of the permitting application.
# Every resource_model JSON in the package EXCEPT these will be (re)imported.
EXCLUDED_RESOURCE_MODELS = {
    "arches_system_settings",
    "publication",
    "legislative_act",
    "contributor",
    "project_sandbox",
    "hca_permit",
    "repository",
    "site_visit",
    "site_submission",
    "hria_discontinued_data",
    "archaeological_site",
}


def _pkg():
    return Path(apps.get_app_config("bcap").path) / "pkg"


def _read_graph_meta(path):
    """Return (graphid, slug) from a graph JSON file."""
    graph = json.loads(Path(path).read_text())["graph"][0]
    return graph["graphid"], graph["slug"]


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
        parser.add_argument(
            "--delete-tiles",
            action="store_true",
            help=(
                "Delete all tiles and resource instances belonging to the reloaded "
                "permit resource models before reimporting."
            ),
        )
        parser.add_argument(
            "--skip-reindex",
            action="store_true",
            help="Skip re-indexing resources in Elasticsearch after reimporting.",
        )

    def handle(self, *args, **options):
        cache.clear()
        if options["delete_tiles"]:
            self.delete_permit_data()
        if not options["skip_graphs"]:
            self.reload_graphs()
        if not options["skip_lists"]:
            self.reload_lists()
        if not options["skip_requirements"]:
            self.reload_requirement_templates()
        if not options["skip_reindex"]:
            self.reindex_resources()

    def reload_graphs(self):
        branches = self._graph_paths("branches", BRANCHES)
        models = self._permit_model_paths()
        for path in branches:
            self.stdout.write(f"  branch:         {Path(path).stem}")
        for path in models:
            _, slug = _read_graph_meta(path)
            self.stdout.write(f"  resource model: {slug}")
        self._prepare_graphs_for_import(branches + models)
        PackagesCommand().import_graphs(branches + models)
        self._publish_and_sync_resources(models)
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(branches)} branches and {len(models)} resource models."
            )
        )

    def _prepare_graphs_for_import(self, paths):
        """For each existing graph: create a draft then promote it.
        promote_draft_graph_to_active_graph calls restore_state_from_serialized_graph,
        which calls delete_associated_entities before recreating nodes/cards/widgets.
        This clears any stale CardXNodeXWidget rows so the subsequent import_graphs
        call can write without hitting duplicate-PK violations."""
        valid_publication_ids = set(
            arches_models.GraphXPublishedGraph.objects.values_list(
                "publicationid", flat=True
            )
        )
        for path in paths:
            graphid, slug = _read_graph_meta(path)
            try:
                source_graph = Graph.objects.get(
                    pk=graphid, source_identifier__isnull=True
                )
            except Graph.DoesNotExist:
                continue  # New graph — no prep needed, import will create it.
            # When a graph is published and has no unpublished changes,
            # get_nodes() reads from published_graphs.serialized_graph (a JSON
            # snapshot) rather than the live nodes table. That snapshot can
            # contain stale sourcebranchpublicationid values even after the
            # live table was cleaned up by on_delete=SET_NULL. refresh_from_database()
            # bypasses should_use_published_graph() and always reads the live table,
            # ensuring create_draft_graph() deep-copies clean in-memory nodes.
            source_graph.refresh_from_database()
            dangling = arches_models.Node.objects.filter(
                graph_id=graphid,
                sourcebranchpublication__isnull=False,
            ).exclude(sourcebranchpublication_id__in=valid_publication_ids)
            if dangling.exists():
                count = dangling.update(sourcebranchpublication=None)
                self.stdout.write(
                    f"  {slug}: cleared {count} dangling sourcebranchpublication refs"
                )
                source_graph.refresh_from_database()
            if not source_graph.get_draft_graph():
                source_graph.create_draft_graph()
            source_graph.promote_draft_graph_to_active_graph()
            self.stdout.write(f"  prepared: {slug}")

    def _publish_and_sync_resources(self, paths):
        for path in paths:
            graphid, slug = _read_graph_meta(path)
            source_graph = Graph.objects.get(pk=graphid, source_identifier__isnull=True)
            source_graph.publish(notes="reload_permit_models")
            updated = (
                arches_models.ResourceInstance.objects.filter(graph_id=graphid)
                .exclude(graph_publication_id=source_graph.publication_id)
                .update(graph_publication_id=source_graph.publication_id)
            )
            if updated:
                self.stdout.write(
                    f"  {slug}: moved {updated} instances to new publication"
                )

    def reindex_resources(self):
        for path in self._permit_model_paths():
            graphid, slug = _read_graph_meta(path)
            call_command("es", "index_resources_by_type", resource_types=[str(graphid)])
            self.stdout.write(self.style.SUCCESS(f"  reindexed: {slug}"))

    def delete_permit_data(self):
        slugs = [_read_graph_meta(p)[1] for p in self._permit_model_paths()]
        graphs = arches_models.GraphModel.objects.filter(slug__in=slugs)
        tile_count, _ = arches_models.TileModel.objects.filter(
            resourceinstance__graph__in=graphs
        ).delete()
        instance_count, _ = arches_models.ResourceInstance.objects.filter(
            graph__in=graphs
        ).delete()
        self.stdout.write(
            self.style.WARNING(
                f"Deleted {tile_count} tiles and {instance_count} resource instances "
                "for permit resource models."
            )
        )

    @staticmethod
    def _permit_model_paths():
        paths = []
        for path in sorted((_pkg() / "graphs" / "resource_models").glob("*.json")):
            if _read_graph_meta(str(path))[1] not in EXCLUDED_RESOURCE_MODELS:
                paths.append(str(path))
        return paths

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
        if not templates_exist():
            raise RuntimeError("Requirement templates missing after reseed.")
