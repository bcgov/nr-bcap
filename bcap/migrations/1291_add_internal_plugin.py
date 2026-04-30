from arches.app.models.models import Plugin
from django.db import migrations

def add_internal_plugin(apps, schema_editor):
    plugin = Plugin()
    plugin.name = {"en": "Internal Permit Dashboard"}
    plugin.icon = "fa fa-share-from-square"
    plugin.component = "views/components/plugins/internal-permit-dashboard"
    plugin.componentname = "internal-permit-dashboard"
    plugin.slug = "internal-permit-dashboard"
    plugin.config = {"show": True, "workflows": []}
    plugin.sortorder = 1
    plugin.save()

def remove_internal_plugin(apps, schema_editor):
    Plugin.objects.get(slug="internal-permit-dashboard").delete()

class Migration(migrations.Migration):
    dependencies = [
        ("bcap", "1290_add_plugin"), # Dependent on your external plugin migration
    ]
    operations = [migrations.RunPython(add_internal_plugin, remove_internal_plugin)]