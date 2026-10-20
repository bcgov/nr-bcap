import os

from django.conf import settings
from django.db import migrations

from arches_controlled_lists.models import List
from arches_controlled_lists.utils.skos import SKOSReader

INDUSTRY_SECTOR_LIST_ID = "553328cc-16ab-4c84-9a15-35e2a4dc90d5"


def load_industry_sector_skos(apps, schema_editor):
    # Remove this later if necessary, this is if you have an existing database.
    if List.objects.filter(pk=INDUSTRY_SECTOR_LIST_ID).exists():
        return

    path = os.path.join(
        settings.APP_ROOT, "pkg", "reference_data", "skos", "industry_sector.xml"
    )
    skos = SKOSReader()
    rdf = skos.read_file(path)
    skos.save_controlled_lists_from_skos(rdf)


class Migration(migrations.Migration):

    dependencies = [("bcap", "1411_update_arch_site_fill_styling")]

    operations = [
        migrations.RunPython(load_industry_sector_skos, migrations.RunPython.noop),
    ]
