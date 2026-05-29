"""Delete the dashboard test data created by the dashboard seeders.

Only resources tagged with the seeder's legacyid marker are removed, so real
data in the same graphs is left untouched. Temporary developer aid; will be
removed in a future release."""

from arches.app.models.models import ResourceInstance
from arches.app.search.mappings import RESOURCES_INDEX, TERMS_INDEX
from arches.app.search.search_engine_factory import SearchEngineFactory

from django.core.management.base import BaseCommand

from bcap.util.dashboard.resource_builder import SEED_LEGACYID_PREFIX


class Command(BaseCommand):
    help = (
        "Delete all dashboard test data created by the dashboard seeders "
        "(matched by the seeder's legacyid marker). Temporary developer aid; "
        "will be removed in a future release."
    )

    def handle(self, *args, **options):
        seeded = ResourceInstance.objects.filter(
            legacyid__startswith=f"{SEED_LEGACYID_PREFIX}:"
        )
        ids = [str(pk) for pk in seeded.values_list("pk", flat=True)]
        if not ids:
            self.stdout.write("No dashboard test data found.")
            return

        se = SearchEngineFactory().create()
        se.delete(
            index=RESOURCES_INDEX, query={"query": {"ids": {"values": ids}}}, refresh=True
        )
        se.delete(
            index=TERMS_INDEX,
            query={"query": {"terms": {"resourceinstanceid": ids}}},
            refresh=True,
        )

        seeded.delete()

        self.stdout.write(
            self.style.SUCCESS(f"Deleted {len(ids)} seeded dashboard resources.")
        )
