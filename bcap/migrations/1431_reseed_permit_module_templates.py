"""Reseed the process-requirement templates so the permit module picks up its
new Initial Submission workflow requirement. Same rebuild as 1423: the specs are
the source of truth, so clear the seeded templates and let the seed command
rebuild from them."""

from django.db import migrations

from bcap.management.commands.seed_template_requirements import reseed_templates


def seed(apps, schema_editor):
    reseed_templates()


class Migration(migrations.Migration):

    # The builder opens its own durable atomic block per save; can't nest.
    atomic = False

    dependencies = [("bcap", "1428_use_aliases_in_get_map_attribute_data")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
