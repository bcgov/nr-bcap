"""Default-deny setup: seed the workflow role groups, drop anonymous from
Resource Exporter (it stays in Guest), and unregister the now-redundant
AdminOnlyAccess / RestrictedSiteAccess functions.

Behavioral change: RestrictedSiteAccess was the function that exposed
public-criteria sites to the anonymous user and the Guest group. Removing it
(together with dropping anonymous from Resource Exporter) means anonymous/Guest
no longer get any site read access -- the system moves to deny-by-default, with
internal access granted per-graph by the permission framework and external
access scoped to a user's own resources at the route layer. This is a
deliberate visibility reduction, not an incidental cleanup.

The function unregistration is intentionally irreversible: this PR also deletes
the AdminOnlyAccess / RestrictedSiteAccess Python modules, so a reverse cannot
restore working function rows. The reverse therefore re-seeds groups and the
anonymous Resource Exporter membership but leaves the functions unregistered."""

from django.db import migrations

ROLE_GROUPS = [
    "Permit Reviewer",
    "Permit Decider",
    "Inventory Reviewer",
    "Inventory Manager",
    "Submitter",
]
ANONYMOUS_USERNAME = "anonymous"
EXPORTER_GROUP = "Resource Exporter"

ADMIN_ONLY = "60000000-0000-0000-0000-000000002002"
RESTRICTED_SITE = "60000000-0000-0000-0000-000000002003"


def create_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in ROLE_GROUPS:
        Group.objects.get_or_create(name=name)


def remove_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=ROLE_GROUPS).delete()


def remove_anonymous_exporter(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Group = apps.get_model("auth", "Group")
    anonymous = User.objects.filter(username=ANONYMOUS_USERNAME).first()
    group = Group.objects.filter(name=EXPORTER_GROUP).first()
    if anonymous is not None and group is not None:
        group.user_set.remove(anonymous)


def restore_anonymous_exporter(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Group = apps.get_model("auth", "Group")
    anonymous = User.objects.filter(username=ANONYMOUS_USERNAME).first()
    group = Group.objects.filter(name=EXPORTER_GROUP).first()
    if anonymous is not None and group is not None:
        group.user_set.add(anonymous)


drop_functions_sql = f"""
    delete from functions_x_graphs
        where functionid in ('{ADMIN_ONLY}', '{RESTRICTED_SITE}');
    delete from functions
        where functionid in ('{ADMIN_ONLY}', '{RESTRICTED_SITE}');
"""

# Irreversible: this PR deletes the AdminOnlyAccess / RestrictedSiteAccess
# Python modules, so re-inserting function rows on reverse would only recreate
# registrations that can't load. The reverse is a no-op -- the groups and the
# anonymous Resource Exporter membership are restored by the RunPython reverses
# above, but the functions stay unregistered.
restore_functions_sql = migrations.RunSQL.noop


class Migration(migrations.Migration):
    dependencies = [
        ("bcap", "1414_add_edit_log_tileinstanceid_index"),
    ]
    operations = [
        migrations.RunPython(create_roles, remove_roles),
        migrations.RunPython(remove_anonymous_exporter, restore_anonymous_exporter),
        migrations.RunSQL(drop_functions_sql, restore_functions_sql),
    ]
