"""Seed the role groups added since 1415, drop the resource-access functions
they replace, and open both dashboards to the branch."""

from django.db import migrations
from guardian.ctypes import get_content_type

from bcap.permissions.groups import Groups

ROLE_GROUPS = [
    Groups.PERMIT_SDM,
    Groups.PERMIT_MANAGER,
    Groups.MPP_SUBMITTER,
]

# The branch reads the applicants' dashboard too, which its API already allows.
# Submitter's grant on submissions is 1432's and stays.
PLUGIN_GRANTS = [
    (Groups.ARCHAEOLOGY_BRANCH, "internal-permit-dashboard"),
    (Groups.ARCHAEOLOGY_BRANCH, "submissions"),
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


def _grant(apps, group_name, componentname):
    """The pieces of the guardian row granting view_plugin on one plugin."""
    plugin = apps.get_model("models", "Plugin").objects.get(componentname=componentname)
    return {
        "permission": apps.get_model("auth", "Permission").objects.get(
            codename="view_plugin"
        ),
        "group": apps.get_model("auth", "Group").objects.get(name=group_name),
        "content_type_id": get_content_type(plugin).pk,
        "object_pk": str(plugin.pk),
    }


def assign_view_plugin(apps, schema_editor):
    """The plugin view redirects to login without this, so a page stays shut to
    a group even where its API is already theirs."""
    # Cannot use django-guardian shortcuts in migrations:
    # https://github.com/django-guardian/django-guardian/issues/751
    rows = apps.get_model("guardian", "GroupObjectPermission").objects
    for group_name, componentname in PLUGIN_GRANTS:
        rows.get_or_create(**_grant(apps, group_name, componentname))


def remove_view_plugin(apps, schema_editor):
    rows = apps.get_model("guardian", "GroupObjectPermission").objects
    for group_name, componentname in PLUGIN_GRANTS:
        rows.filter(**_grant(apps, group_name, componentname)).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bcap", "1434_boolean_checkbox_widget_mapping"),
        ("guardian", "0002_generic_permissions_index"),
    ]

    operations = [
        migrations.RunPython(create_role_groups, delete_role_groups),
        migrations.RunPython(remove_functions, migrations.RunPython.noop),
        migrations.RunPython(assign_view_plugin, remove_view_plugin),
    ]
