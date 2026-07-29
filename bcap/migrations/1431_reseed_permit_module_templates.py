"""Reseed the process-requirement templates so the permit module picks up its
new Initial Submission workflow requirement. Same rebuild as 1423: the specs are
the source of truth, so clear the seeded templates and let the seed command
rebuild from them."""

from django.core.management import call_command
from django.db import migrations

from arches.app.models.resource import Resource

from bcap.management.commands.seed_template_requirements import (
    Command as SeedTemplatesCommand,
)
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)


def seed(apps, schema_editor):
    for template in ProcessRequirementService()._templates_by_id().values():
        Resource.objects.get(pk=template.pk).delete()
    call_command("seed_template_requirements")
    if not SeedTemplatesCommand._templates_exist():
        raise RuntimeError("Requirement templates missing after reseed.")


class Migration(migrations.Migration):

    # The builder opens its own durable atomic block per save; can't nest.
    atomic = False

    dependencies = [("bcap", "1430_create_databc_api_views")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
