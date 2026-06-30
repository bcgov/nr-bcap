"""Shared logic for the dashboard seeding commands: build a permit graph through
a builder, optionally index it in Elasticsearch, and report the permit's editor
URL. The leading underscore keeps Django's command loader from picking this up
as a runnable command."""

from arches.app.models.resource import Resource

from django.core.management.base import BaseCommand, CommandError

from bcap.util.indexing import bulk_index as _bulk_index
from bcap.util.links import app_url


def _resource_url(pk):
    """Resource editor URL (eg http://localhost:82/bcap/resource/<id>)."""
    return app_url(f"resource/{pk}")


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
        # One builder per run so its graph cache and shared resources are reused.
        builder = self.builder_class()
        with builder.deferred_descriptors():
            shared = builder.build_shared()
            # Shared resources are the same objects on every card; collect once.
            assignees = shared.assignees
            resources = [
                *shared.project_officers,
                *shared.requirement_templates,
                *assignees,
                *(hca.permit for hca in shared.hca_permits),
                *(holder for hca in shared.hca_permits for holder in hca.holders),
            ]
            # No outer transaction: each save opens its own durable atomic block.
            for i in range(count):
                # Seed the unassigned permit only on the first card.
                builder._SEED_UNASSIGNED_PERMIT = i == 0
                data = builder.build(shared=shared)

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
                        *data.process_requirements,
                    ]
                )

        if not options["no_index"]:
            _bulk_index(resources)

        for label, permit in permits:
            self.stdout.write(self.style.SUCCESS(f"Created {label} {permit.pk}"))
            self.stdout.write(f"  can be accessed at {_resource_url(permit.pk)}")

        # matches a ministry assignee by the logged-in user's bcap_username, so
        # surface the assignee ids (with names) for reference.
        self.stdout.write("Ministry assignee Contributor ids:")
        for assignee in assignees:
            name = Resource.objects.get(pk=assignee.pk).displayname()
            self.stdout.write(f"  {assignee.pk}  {name}")

        if options["no_index"]:
            self.stdout.write("Skipped indexing (--no-index).")
