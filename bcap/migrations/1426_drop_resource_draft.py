"""Drop the ResourceDraft table (drafts are now 'drafts' graph resources, see
DraftService) and reload the process-requirement templates so the DB matches the
changed module group files. Drafts are ephemeral, so no draft data migration."""

from django.core.management import call_command
from django.db import migrations

from arches.app.models.resource import Resource

from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)


def _clear_templates():
    for template in ProcessRequirementService()._templates_by_id().values():
        Resource.objects.get(pk=template.pk).delete()


def reload_templates(apps, schema_editor):
    # Clear first so the create-if-missing seed rebuilds every template from the
    # current module group files.
    _clear_templates()
    call_command("seed_template_requirements")


def remove_templates(apps, schema_editor):
    _clear_templates()


class Migration(migrations.Migration):

    # The builder opens its own durable atomic block per save; can't nest.
    atomic = False

    dependencies = [
        ("bcap", "1425_process_module_ids"),
    ]

    operations = [
        migrations.DeleteModel(name="ResourceDraft"),
        migrations.RunPython(reload_templates, remove_templates),
    ]
