import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models

ROLE_GROUPS = [
    "Permit Reviewer",
    "Permit Decider",
    "Inventory Reviewer",
    "Inventory Manager",
    "Submitter",
]


def create_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in ROLE_GROUPS:
        Group.objects.get_or_create(name=name)


def delete_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=ROLE_GROUPS).delete()


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
    ]
