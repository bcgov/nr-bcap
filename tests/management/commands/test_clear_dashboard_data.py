from django.core.management import call_command
from django.test import TestCase

from arches.app.models.models import ResourceInstance

from bcap.util.dashboard.dashboard_seed import DashboardDemoBuilder
from bcap.util.dashboard.resource_builder import SEED_LEGACYID_PREFIX

from tests.controlled_list_fixtures import SeedControlledListsMixin


class ClearDashboardDataCommandTests(SeedControlledListsMixin, TestCase):
    """clear_dashboard_data deletes only the seeder-tagged resources."""

    def test_deletes_seed_tagged_resources_and_keeps_others(self):
        data = DashboardDemoBuilder().build()

        # An untagged resource on the same graph must survive the clear.
        untagged = ResourceInstance.objects.get(pk=data.holders[0].pk)
        untagged.legacyid = None
        untagged.save()

        tagged_pks = list(
            ResourceInstance.objects.filter(
                legacyid__startswith=f"{SEED_LEGACYID_PREFIX}:"
            ).values_list("pk", flat=True)
        )
        self.assertIn(data.permit.pk, tagged_pks)

        call_command("clear_dashboard_data")

        self.assertFalse(
            ResourceInstance.objects.filter(pk__in=tagged_pks).exists()
        )
        self.assertTrue(
            ResourceInstance.objects.filter(pk=untagged.pk).exists()
        )

    def test_reports_when_nothing_to_delete(self):
        out = []
        call_command("clear_dashboard_data", stdout=_Collector(out))
        self.assertIn("No dashboard test data found.", "".join(out))


class _Collector:
    def __init__(self, sink):
        self._sink = sink

    def write(self, msg):
        self._sink.append(msg)
