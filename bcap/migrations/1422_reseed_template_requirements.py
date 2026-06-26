"""Re-seed the process-requirement templates against the refined model: the
original seed (1416) created them in the old nodegroup shape."""

from django.core.management import call_command
from django.db import migrations

from arches.app.models.resource import Resource

from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)


def reseed_template_requirements(apps, schema_editor):
    service = ProcessRequirementService()
    existing = service._templates_by_name()
    for name in service._TEMPLATE_NAMES:
        template = existing.get(name)
        if template is not None:
            Resource.objects.get(pk=template.pk).delete()
    call_command("seed_template_requirements")


class Migration(migrations.Migration):

    # The seed opens its own durable atomic block per save; can't nest.
    atomic = False

    dependencies = [
        ("bcap", "1421_load_process_requirement_type_skos"),
        ("models", "12394_resource_identifier"),
    ]

    operations = [
        migrations.RunPython(reseed_template_requirements, migrations.RunPython.noop),
    ]
