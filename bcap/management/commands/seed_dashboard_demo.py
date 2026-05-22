"""Persist the dashboard demo graph (the same data the dashboard service tests
build) to the current database so it can be viewed in the app.

Temporary: this is a developer aid for building out the dashboard and will be
removed in a future release."""

from arches.app.models.resource import Resource

from django.conf import settings
from django.core.management.base import BaseCommand

from bcap.util.dashboard_seed import DashboardDemoBuilder


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
            # The builder saves with index=False, so nothing is in Elasticsearch
            # yet; index each resource so it shows up in search.
            for resource in resources:
                Resource.objects.get(pk=resource.pk).index()

        self.stdout.write(
            self.style.SUCCESS(f"Created Permit Application {data.permit.pk}")
        )
        self.stdout.write(f"  can be accessed at {_resource_url(data.permit.pk)}")
        self.stdout.write(
            f"  process_requirement: {data.process_requirements[0].pk}"
        )
        if options["no_index"]:
            self.stdout.write("Skipped indexing (--no-index).")
