"""Persist just the process-requirement templates (the is_template_requirement
set that the application clones working copies from), without the rest of the
demo permit application."""

from django.core.management.base import BaseCommand

from bcap.management.commands._dashboard_seed_base import _bulk_index, _resource_url
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.services.process_requirement.template_specs import (
    flatten,
    supported_permit_types,
)
from bcap.util.dashboard.requirement_flow_seed import RequirementFlowBuilder


def _all_specs():
    """Every module's grouping parent and child requirements, flattened."""
    return [spec for module in supported_permit_types() for spec in flatten(module)]


class Command(BaseCommand):
    help = (
        "Create the process-requirement templates only (no permit application), "
        "if they don't already exist."
    )

    def handle(self, *args, **options):
        if self._templates_exist():
            self.stdout.write("Requirement templates already exist; nothing to do.")
            return

        builder = RequirementFlowBuilder()
        with builder.deferred_descriptors():
            templates = builder.make_requirement_templates(_all_specs())

        _bulk_index(templates)

        for template in templates:
            self.stdout.write(
                self.style.SUCCESS(f"Created requirement template {template.pk}")
            )
            self.stdout.write(f"  can be accessed at {_resource_url(template.pk)}")

    @staticmethod
    def _templates_exist():
        """Whether every module's templates the application clones from already
        exist. Other (e.g. demo) templates don't count -- those wouldn't be found
        by id when cloning working copies."""
        by_id = ProcessRequirementService()._templates_by_id()
        return all(spec["id"] in by_id for spec in _all_specs())
