"""Delete the dashboard test data created by the dashboard seeders.

Only resources tagged with the seeder's legacyid marker are removed, so real
data in the same graphs is left untouched. Temporary developer aid; will be
removed in a future release."""

from arches.app.models.resource import Resource

from django.core.management.base import BaseCommand

from bcap.util.dashboard.resource_builder import SEED_LEGACYID_PREFIX


class Command(BaseCommand):
    help = (
        "Delete all dashboard test data created by the dashboard seeders "
        "(matched by the seeder's legacyid marker). Temporary developer aid; "
        "will be removed in a future release."
    )

    def handle(self, *args, **options):
        seeded = Resource.objects.filter(
            legacyid__startswith=f"{SEED_LEGACYID_PREFIX}:"
        )
        count = seeded.count()
        if count == 0:
            self.stdout.write("No dashboard test data found.")
            return

        # Delete one at a time so each resource is removed from the search
        # index too (a queryset .delete() would skip that).
        for resource in seeded.iterator():
            resource.delete()

        self.stdout.write(
            self.style.SUCCESS(f"Deleted {count} seeded dashboard resources.")
        )
