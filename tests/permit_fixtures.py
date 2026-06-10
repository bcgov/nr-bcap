"""Shared fixtures for the permit-application / process-requirement tests."""

from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)


def make_template(builder, name, subs=(("Sub-1", False, 1),)):
    """A process-requirement template (is_template_requirement=True) named
    ``name``, with the given (sub_name, satisfied, sort_order) sub-requirements."""
    return builder.make_process_requirement(
        {
            "id": f"REQ-{name[:4].upper()}",
            "name": name,
            "due": "2026-02-01",
            "notes": "",
            "satisfied": False,
            "is_template": True,
            "sub_requirements": [
                {
                    "name": sub_name,
                    "description": f"{sub_name} description",
                    "mandatory": True,
                    "sub_satisfied": satisfied,
                    "sort_order": sort_order,
                }
                for sub_name, satisfied, sort_order in subs
            ],
        }
    )


def seed_requirement_templates(builder):
    """One template per name the service expects, in flow order."""
    return [
        make_template(builder, name)
        for name in ProcessRequirementService._TEMPLATE_NAMES
    ]
