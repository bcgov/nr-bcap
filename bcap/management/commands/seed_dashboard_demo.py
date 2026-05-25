"""Persist the dashboard demo graph (the same data the dashboard service tests
build) to the current database so it can be viewed in the app.

Temporary: this is a developer aid for building out the dashboard and will be
removed in a future release."""

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models import models
from arches.app.models.resource import Resource
from arches.app.search.mappings import RESOURCES_INDEX, TERMS_INDEX
from arches.app.search.search_engine_factory import SearchEngineFactory

from django.conf import settings
from django.core.management.base import BaseCommand

from bcap.util.dashboard.dashboard_seed import DashboardDemoBuilder


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


class Command(BaseCommand):
    help = (
        "Create the dashboard demo Permit Application (and its related Process "
        "Requirement, HCA Permit, and Contributors) in the current database. "
        "Temporary developer aid; will be removed in a future release."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-index",
            action="store_true",
            help="Skip Elasticsearch indexing (use when ES is not running).",
        )

    def handle(self, *args, **options):
        # No outer transaction: arches-querysets saves open a durable atomic
        # block, which cannot be nested inside another atomic.
        data = DashboardDemoBuilder().build()

        resources = [
            data.permit,
            data.hca_permit,
            *data.process_requirements,
            *data.assignees,
            *data.holders,
        ]
        if not options["no_index"]:
            _bulk_index(resources)

        self.stdout.write(
            self.style.SUCCESS(f"Created Permit Application {data.permit.pk}")
        )
        self.stdout.write(f"  can be accessed at {_resource_url(data.permit.pk)}")
        if options["no_index"]:
            self.stdout.write("Skipped indexing (--no-index).")
