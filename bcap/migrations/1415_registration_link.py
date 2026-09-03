import django.db.models.deletion
import uuid

from arches.app.models.models import Plugin

from django.conf import settings
from django.db import migrations, models

ROLE_GROUPS = [
    "Permit Reviewer",
    "Permit Decider",
    "Inventory Reviewer",
    "Inventory Manager",
    "Submitter",
]

# Named by the permission defaults and read by later migrations, but created
# nowhere else. Kept on reverse: it carries real memberships, and dropping it
# would take their access with it.
PERMANENT_GROUPS = [
    "Archaeology Branch",
]

CONTRIBUTOR_INVITATIONS_PLUGIN_SLUG = "contributor-invitations"


def create_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in ROLE_GROUPS + PERMANENT_GROUPS:
        Group.objects.get_or_create(name=name)


def delete_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=ROLE_GROUPS).delete()


def add_contributor_invitations_plugin(apps, schema_editor):
    if Plugin.objects.filter(slug=CONTRIBUTOR_INVITATIONS_PLUGIN_SLUG).exists():
        return

    Plugin.objects.create(
        name={"en": "Contributor Invitations"},
        icon="fa fa-user-plus",
        component="views/components/plugins/contributor-invitations",
        componentname="contributor-invitations",
        config={"show": True},
        slug="contributor-invitations",
        sortorder=2,
    )


def remove_contributor_invitations_plugin(apps, schema_editor):
    Plugin.objects.filter(slug=CONTRIBUTOR_INVITATIONS_PLUGIN_SLUG).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bcap", "1414_add_edit_log_tileinstanceid_index"),
        ("auth", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RegistrationLink",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("contributor_id", models.UUIDField(blank=True, null=True)),
                ("new_contributor", models.JSONField(blank=True, null=True)),
                ("groups", models.JSONField(blank=True, default=list)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("expires", models.DateTimeField()),
                ("used", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="registration_links_issued",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "used_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="registration_links_used",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Registration Link",
                "verbose_name_plural": "Registration Links",
                "db_table": "bcap_registration_links",
                "indexes": [
                    models.Index(
                        fields=["contributor_id"],
                        name="bcap_regis_contrib_idx",
                    )
                ],
            },
        ),
        migrations.RunPython(create_role_groups, delete_role_groups),
        migrations.RunPython(
            add_contributor_invitations_plugin,
            remove_contributor_invitations_plugin,
        ),
    ]
