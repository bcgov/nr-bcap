"""Originally reseeded the process-requirement templates against the refined
model. Now a no-op: 1416's seed command produces the refined, grouped templates
directly, and 1424 regroups any pre-existing flat set. Kept as an
already-applied marker that later migrations depend on."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bcap", "1421_load_process_requirement_type_skos"),
        ("models", "12394_resource_identifier"),
    ]

    noop = migrations.RunPython.noop
    operations = [migrations.RunPython(noop, noop)]
