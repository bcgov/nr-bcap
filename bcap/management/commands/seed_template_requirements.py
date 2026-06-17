"""Persist just the process-requirement templates (the is_template_requirement
set that the application clones working copies from), without the rest of the
demo permit application."""

from django.core.management.base import BaseCommand

from arches.app.models.models import Node, TileModel

from bcap.management.commands._dashboard_seed_base import _bulk_index, _resource_url
from bcap.util.dashboard.requirement_flow_seed import RequirementFlowBuilder


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
            templates = builder.make_requirement_templates(builder._requirement_specs())

        _bulk_index(templates)

        for template in templates:
            self.stdout.write(
                self.style.SUCCESS(f"Created requirement template {template.pk}")
            )
            self.stdout.write(f"  can be accessed at {_resource_url(template.pk)}")

    @staticmethod
    def _templates_exist():
        """Whether the is_template_requirement set has already been seeded."""
        node = Node.objects.filter(
            graph__slug="process_requirement",
            alias="is_template_requirement",
            source_identifier=None,
        ).first()
        return bool(
            node
            and TileModel.objects.filter(
                nodegroup_id=node.nodegroup_id,
                data__contains={str(node.nodeid): True},
            ).exists()
        )
