"""Seed the process-requirement templates for every module (permit,
investigation) from pkg/reference_data/process_requirements/modules, each under
its grouping parent. Clears any earlier-seeded templates first so it also
regroups the permit set and renumbers investigation, subsuming the separate
permit-regroup and investigation seeds."""

from django.db import migrations

from arches.app.models.resource import Resource

from bcap.management.commands._dashboard_seed_base import _bulk_index
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.services.process_requirement.template_specs import (
    flatten,
    supported_permit_types,
)
from bcap.util.dashboard.requirement_flow_seed import RequirementFlowBuilder


def _specs():
    """Every module's grouping parent and child requirements, flattened."""
    return [spec for module in supported_permit_types() for spec in flatten(module)]


def seed(apps, schema_editor):
    for template in ProcessRequirementService()._templates_by_id().values():
        Resource.objects.get(pk=template.pk).delete()
    builder = RequirementFlowBuilder()
    with builder.deferred_descriptors():
        templates = [
            builder.make_process_requirement({**spec, "is_template": True})
            for spec in _specs()
        ]
    _bulk_index(templates)


def remove(apps, schema_editor):
    by_id = ProcessRequirementService()._templates_by_id()
    for spec in _specs():
        template = by_id.get(spec["id"])
        if template is not None:
            Resource.objects.get(pk=template.pk).delete()


class Migration(migrations.Migration):

    # The builder opens its own durable atomic block per save; can't nest.
    atomic = False

    dependencies = [
        ("bcap", "1422_reseed_template_requirements"),
        ("models", "12394_resource_identifier"),
    ]

    operations = [migrations.RunPython(seed, remove)]
