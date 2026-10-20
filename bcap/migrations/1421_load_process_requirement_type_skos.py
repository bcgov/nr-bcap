import os

from django.conf import settings
from django.db import migrations

from arches_controlled_lists.models import List
from arches_controlled_lists.utils.skos import SKOSReader

PROCESS_REQUIREMENT_TYPE_LIST_ID = "b35aa446-66a0-4ab0-95cf-c51bf1d043d4"


def load_process_requirement_type_skos(apps, schema_editor):
    # Skip if the list already exists on an established database.
    if List.objects.filter(pk=PROCESS_REQUIREMENT_TYPE_LIST_ID).exists():
        return

    path = os.path.join(
        settings.APP_ROOT,
        "pkg",
        "reference_data",
        "skos",
        "process_requirement_type.xml",
    )
    skos = SKOSReader()
    rdf = skos.read_file(path)
    skos.save_controlled_lists_from_skos(rdf)


class Migration(migrations.Migration):

    dependencies = [("bcap", "1420_geojson_refresh_jit_off")]

    operations = [
        migrations.RunPython(
            load_process_requirement_type_skos, migrations.RunPython.noop
        ),
    ]
