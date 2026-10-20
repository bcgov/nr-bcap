"""Register the clone-process-requirement-templates function. The permit
application graph's functions_x_graphs entry attaches it to the
process_requirement nodegroup; this just creates the function row it references.
Must run before the graph is (re)imported."""

from django.db import migrations

FUNCTIONID = "60000000-0000-0000-0000-000000002010"


def register(apps, schema_editor):
    Function = apps.get_model("models", "Function")
    Function.objects.update_or_create(
        functionid=FUNCTIONID,
        defaults={
            "name": "Clone Process Requirement Templates",
            "functiontype": "node",
            "description": (
                "On a permit application save, swaps a linked process-requirement "
                "template for a freshly cloned working copy."
            ),
            "defaultconfig": {"triggering_nodegroups": []},
            "modulename": "clone_process_requirement_templates.py",
            "classname": "CloneProcessRequirementTemplates",
            "component": "",
        },
    )


def unregister(apps, schema_editor):
    Function = apps.get_model("models", "Function")
    Function.objects.filter(functionid=FUNCTIONID).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("bcap", "1417_permit_application_id_sequence"),
    ]

    operations = [
        migrations.RunPython(register, unregister),
    ]
