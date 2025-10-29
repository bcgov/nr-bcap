from django.db import migrations
from arches.app.models.models import Plugin


def show_etl_plugin_by_default(apps, schema_editor):
    plugin = Plugin.objects.filter(slug="bulk-data-manager").first()
    plugin.config.raw_value["show"] = True
    plugin.save()


def hide_etl_plugin_by_default(apps, schema_editor):
    plugin = Plugin.objects.filter(slug="bulk-data-manager").first()
    plugin.config.raw_value["show"] = False
    plugin.save()


class Migration(migrations.Migration):

    dependencies = [
        ("bcap", "1031_add_borden_number_counter_model"),
    ]

    operations = [
        migrations.RunPython(show_etl_plugin_by_default, hide_etl_plugin_by_default)
    ]
