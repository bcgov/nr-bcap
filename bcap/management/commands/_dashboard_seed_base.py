"""Shared logic for the dashboard seeding commands: build a permit graph through
a builder, optionally index it in Elasticsearch, and report the permit's editor
URL. The leading underscore keeps Django's command loader from picking this up
as a runnable command."""

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models import models
from arches.app.models.resource import Resource
from arches.app.search.mappings import RESOURCES_INDEX, TERMS_INDEX
from arches.app.search.search_engine_factory import SearchEngineFactory

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def _bulk_index(resources):
    """Index the given (already-saved) resources in one bulk request rather than
    one Elasticsearch round-trip per resource."""
    se = SearchEngineFactory().create()
    datatype_factory = DataTypeFactory()
    node_datatypes = {
        str(nodeid): datatype
        for nodeid, datatype in models.Node.objects.values_list("nodeid", "datatype")
    }

    def bulk_items(resource):
        """The resource's search document plus its term documents, as ES bulk items."""
        document, terms = resource.get_documents_to_index(
            datatype_factory=datatype_factory, node_datatypes=node_datatypes
        )
        yield se.create_bulk_item(
            index=RESOURCES_INDEX, id=document["resourceinstanceid"], data=document
        )
        for term in terms:
            yield se.create_bulk_item(
                index=TERMS_INDEX, id=term["_id"], data=term["_source"]
            )

    se.bulk_index(
        item for r in resources for item in bulk_items(Resource.objects.get(pk=r.pk))
    )


def _resource_url(pk):
    """Resource editor URL, honouring the app's origin and sub-path mount
    (eg http://localhost:82/bcap/resource/<id>)."""
    origin = (settings.PUBLIC_ORIGIN or "").rstrip("/")
    # The app is mounted under /bcap (see VITE_BASE etc.); FORCE_SCRIPT_NAME
    # overrides that when set.
    prefix = (settings.FORCE_SCRIPT_NAME or "/bcap/").strip("/")
    return f"{origin}/{prefix}/resource/{pk}"


class DashboardSeedCommand(BaseCommand):
    """Base for the dashboard seeders. Subclasses set ``builder_class`` (a
    ``DashboardDemoBuilder`` or subclass) and ``help``.

    Temporary developer aid; will be removed in a future release."""

    builder_class = None

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-index",
            action="store_true",
            help="Skip Elasticsearch indexing (use when ES is not running).",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=1,
            help="Number of permit cards to create (default: 1).",
        )

    def handle(self, *args, **options):
        count = options["count"]
        if count < 1:
            raise CommandError("--count must be at least 1.")

        permits = []
        resources = []
        assignees = []
        # No outer transaction: arches-querysets saves open a durable atomic
        # block, which cannot be nested inside another atomic.
        for i in range(count):
            builder = self.builder_class()
            # Seed the demo's unassigned permit only once; the extra cards are
            # ordinary assigned permits.
            if i > 0:
                builder._SEED_UNASSIGNED_PERMIT = False
            data = builder.build()

            permits.append(("Permit Application", data.permit))
            if data.unassigned_permit is not None:
                permits.append(
                    ("Unassigned Permit Application", data.unassigned_permit)
                )
            resources.extend(
                [
                    data.permit,
                    *(
                        [data.unassigned_permit]
                        if data.unassigned_permit is not None
                        else []
                    ),
                    data.hca_permit,
                    data.project_officer,
                    *data.process_requirements,
                    *data.assignees,
                    *data.holders,
                ]
            )
            assignees.extend(data.assignees)

        if not options["no_index"]:
            _bulk_index(resources)

        for label, permit in permits:
            self.stdout.write(self.style.SUCCESS(f"Created {label} {permit.pk}"))
            self.stdout.write(f"  can be accessed at {_resource_url(permit.pk)}")

        # The dashboard's contributor_id filter matches a ministry assignee, so
        # surface the assignee ids (with names) to filter by.
        self.stdout.write("Contributor ids for contributor_id filtering:")
        for assignee in assignees:
            name = Resource.objects.get(pk=assignee.pk).displayname()
            self.stdout.write(f"  {assignee.pk}  {name}")

        if options["no_index"]:
            self.stdout.write("Skipped indexing (--no-index).")
