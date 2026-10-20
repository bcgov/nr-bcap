"""Backing for the unique process module id: a database-wide sequence, and the
save function that mints module ids and stamps their requirements. The Permit
Application graph's functions_x_graphs entry attaches the function to the
process_module nodegroup; this creates the sequence and the function row."""

from django.db import migrations

FUNCTIONID = "60000000-0000-0000-0000-000000002012"

# The plugin was first seeded under the old slug and name; rename the existing
# row (slug, component, name) to match. Remove once every environment loads it
# correctly on first seed.
OLD_PLUGIN_SLUG = "external-permit-workflows"
NEW_PLUGIN_SLUG = "submissions"
OLD_PLUGIN_NAME = {"en": "External Permit Submissions"}
NEW_PLUGIN_NAME = {"en": "Submissions"}


def rename_plugin(apps, schema_editor):
    Plugin = apps.get_model("models", "Plugin")
    Plugin.objects.filter(slug=OLD_PLUGIN_SLUG).update(
        slug=NEW_PLUGIN_SLUG,
        componentname=NEW_PLUGIN_SLUG,
        component=f"views/components/plugins/{NEW_PLUGIN_SLUG}",
        name=NEW_PLUGIN_NAME,
    )


def restore_plugin(apps, schema_editor):
    Plugin = apps.get_model("models", "Plugin")
    Plugin.objects.filter(slug=NEW_PLUGIN_SLUG).update(
        slug=OLD_PLUGIN_SLUG,
        componentname=OLD_PLUGIN_SLUG,
        component=f"views/components/plugins/{OLD_PLUGIN_SLUG}",
        name=OLD_PLUGIN_NAME,
    )


def register(apps, schema_editor):
    Function = apps.get_model("models", "Function")
    Function.objects.update_or_create(
        functionid=FUNCTIONID,
        defaults={
            "name": "Assign Module Ids",
            "functiontype": "node",
            "description": (
                "On a permit application save, mints a module's unique id when "
                "missing and stamps its process requirements with ids derived "
                "from it."
            ),
            "defaultconfig": {"triggering_nodegroups": []},
            "modulename": "assign_module_ids.py",
            "classname": "AssignModuleIds",
            "component": "",
        },
    )


def unregister(apps, schema_editor):
    Function = apps.get_model("models", "Function")
    Function.objects.filter(functionid=FUNCTIONID).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("bcap", "1424_seed_archeology_org_and_modules"),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE SEQUENCE IF NOT EXISTS bcap_process_module_id_seq",
            reverse_sql="DROP SEQUENCE IF EXISTS bcap_process_module_id_seq",
        ),
        migrations.RunPython(register, unregister),
        migrations.RunPython(rename_plugin, restore_plugin),
    ]
