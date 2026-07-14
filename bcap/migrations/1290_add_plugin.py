from arches.app.models.models import Plugin

from django.db import migrations


def add_plugin_config(apps, schema_editor):
    plugin = Plugin()
    plugin.name = {"en": "Submissions"}
    plugin.icon = "fa fa-play-circle"
    plugin.component = "views/components/plugins/submissions"
    plugin.componentname = "submissions"
    plugin.slug = "submissions"
    plugin.config = {"show": True, "workflows": []}
    plugin.sortorder = 0
    plugin.save()


def remove_plugin_config(apps, schema_editor):
    plugin = Plugin.objects.get(slug="submissions")
    plugin.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bcap", "855_add_qgis_views"),
    ]

    operations = [migrations.RunPython(add_plugin_config, remove_plugin_config)]
