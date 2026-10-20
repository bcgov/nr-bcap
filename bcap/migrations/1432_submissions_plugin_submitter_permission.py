from django.db import migrations
from guardian.ctypes import get_content_type


def assign_view_plugin(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Plugin = apps.get_model("models", "Plugin")
    Permission = apps.get_model("auth", "Permission")
    GroupObjectPermission = apps.get_model("guardian", "GroupObjectPermission")

    view_plugin = Permission.objects.get(codename="view_plugin")
    submitter = Group.objects.get(name="Submitter")
    submissions = Plugin.objects.get(componentname="submissions")

    # Cannot use django-guardian shortcuts in migrations:
    # https://github.com/django-guardian/django-guardian/issues/751
    GroupObjectPermission(
        permission=view_plugin,
        group=submitter,
        content_type_id=get_content_type(submissions).pk,
        object_pk=str(submissions.pk),
    ).save()


def remove_view_plugin(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Plugin = apps.get_model("models", "Plugin")
    Permission = apps.get_model("auth", "Permission")
    GroupObjectPermission = apps.get_model("guardian", "GroupObjectPermission")

    view_plugin = Permission.objects.get(codename="view_plugin")
    submitter = Group.objects.get(name="Submitter")
    submissions = Plugin.objects.get(componentname="submissions")

    GroupObjectPermission.objects.filter(
        permission=view_plugin,
        group=submitter,
        content_type_id=get_content_type(submissions).pk,
        object_pk=str(submissions.pk),
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bcap", "1431_reseed_permit_module_templates"),
        ("guardian", "0002_generic_permissions_index"),
    ]

    operations = [
        migrations.RunPython(assign_view_plugin, remove_view_plugin),
    ]
