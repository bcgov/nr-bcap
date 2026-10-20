"""Seed the process-requirement templates (the is_template_requirement set the
application clones working copies from) if none exist yet."""

from django.core.management import call_command
from django.db import migrations


def seed_template_requirements(apps, schema_editor):
    # The command is idempotent: it no-ops if the templates already exist.
    call_command("seed_template_requirements")


class Migration(migrations.Migration):

    # The seed saves through arches_querysets, which opens its own durable
    # atomic block per save, which can't nest in the migration's transaction.
    atomic = False

    dependencies = [
        ("bcap", "1415_registration_link"),
    ]

    # Reverse is a no-op: seeded reference data is left in place on rollback.
    operations = [
        migrations.RunPython(seed_template_requirements, migrations.RunPython.noop),
    ]
