"""Seed the role groups added since 1415 and drop the resource-access functions
they replace. Group names are repeated literally here, as migrations must."""

from django.db import migrations

ROLE_GROUPS = [
    "Permit SDM",
    "Permit Manager",
    "MPP Submitter",
]

# Their per-instance no_access grants are superseded by the default-deny
# framework, and the modules are gone, so any lingering attachment would raise
# ImportError on tile save.
FUNCTION_IDS = [
    "60000000-0000-0000-0000-000000002002",  # Resource Admin Only Access
    "60000000-0000-0000-0000-000000002003",  # Restricted Site Only Access
]


def create_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in ROLE_GROUPS:
        Group.objects.get_or_create(name=name)


def delete_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=ROLE_GROUPS).delete()


def remove_functions(apps, schema_editor):
    apps.get_model("models", "FunctionXGraph").objects.filter(
        function_id__in=FUNCTION_IDS
    ).delete()
    apps.get_model("models", "Function").objects.filter(
        functionid__in=FUNCTION_IDS
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bcap", "1433_create_databc_views"),
    ]

    operations = [
        migrations.RunPython(create_role_groups, delete_role_groups),
        migrations.RunPython(remove_functions, migrations.RunPython.noop),
    ]
