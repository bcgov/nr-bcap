from arches.app.models.models import Plugin

from django.db import migrations


def add_plugin_config(apps, schema_editor):
    plugin = Plugin()
    plugin.name = {"en": "External Permit Submissions"}
    plugin.icon = "fa fa-play-circle"
    plugin.component = "views/components/plugins/external-permit-workflows"
    plugin.componentname = "external-permit-workflows"
    plugin.slug = "external-permit-workflows"
    plugin.config = {"show": True, "workflows": []}
    plugin.sortorder = 0
    plugin.save()


def remove_plugin_config(apps, schema_editor):
    plugin = Plugin.objects.get(slug="external-permit-workflows")
    plugin.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bcap", "855_add_qgis_views"),
    ]

    operations = [migrations.RunPython(add_plugin_config, remove_plugin_config)]
