"""A sequence backing the permit application id, assigned on submission."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("bcap", "1416_seed_template_requirements"),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE SEQUENCE IF NOT EXISTS bcap_permit_application_id_seq",
            reverse_sql="DROP SEQUENCE IF EXISTS bcap_permit_application_id_seq",
        ),
    ]
