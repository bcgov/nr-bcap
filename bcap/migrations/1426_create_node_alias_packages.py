from django.core.management import call_command
from django.db import migrations


def create_node_alias_packages(apps, schema_editor):
    call_command("create_node_alias_packages")


class Migration(migrations.Migration):

    dependencies = [
        ("bcap", "1425_process_module_ids"),
    ]

    operations = [
        migrations.RunPython(create_node_alias_packages, migrations.RunPython.noop),
    ]
