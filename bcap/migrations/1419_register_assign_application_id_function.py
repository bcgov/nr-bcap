"""Register the assign-application-id function. The permit application graph's
functions_x_graphs entry attaches it to the application_identification
nodegroup; this just creates the function row it references. Must run before the
graph is (re)imported."""

from django.db import migrations

FUNCTIONID = "60000000-0000-0000-0000-000000002011"


def register(apps, schema_editor):
    Function = apps.get_model("models", "Function")
    Function.objects.update_or_create(
        functionid=FUNCTIONID,
        defaults={
            "name": "Assign Application Id",
            "functiontype": "node",
            "description": (
                "On a permit application save, assigns a fresh sequence "
                "application id when it is missing or was copied from another "
                "resource."
            ),
            "defaultconfig": {"triggering_nodegroups": []},
            "modulename": "assign_application_id.py",
            "classname": "AssignApplicationId",
            "component": "",
        },
    )


def unregister(apps, schema_editor):
    Function = apps.get_model("models", "Function")
    Function.objects.filter(functionid=FUNCTIONID).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("bcap", "1418_register_clone_requirement_function"),
    ]

    operations = [
        migrations.RunPython(register, unregister),
    ]
