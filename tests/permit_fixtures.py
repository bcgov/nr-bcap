"""Shared fixtures for the permit-application / process-requirement tests."""

from dataclasses import dataclass
from uuid import uuid4

from bcap.util.aliases.permit_application import (
    PermitApplicationAliases as pa,
    PermitApplicationGroupAliases as pa_groups,
)
from bcap.util.controlled_list import reference_value

# Distinct test template names; ids are derived from the full name so they never
# collide (unlike a truncated prefix).
_TEMPLATE_NAMES = ("Recommend Referral", "Recommend Decision", "Decision Summary")


def make_template(builder, name, subs=(("Sub-1", False, 1),)):
    """A process-requirement template (is_template_requirement=True) named
    ``name``, with the given (sub_name, satisfied, sort_order) sub-requirements."""
    return builder.make_process_requirement(
        {
            "id": f"REQ-{name.upper().replace(' ', '-')}",
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
    """One template per test name, in flow order."""
    return [make_template(builder, name) for name in _TEMPLATE_NAMES]


@dataclass
class RequirementRow:
    """A process_requirement child to nest under a module: the requirement
    resource (None for a blank child), its order, and its ministry assignee."""

    requirement: object = None
    order: int = 1
    assignee: object = None


def attach_module(builder, admin, rows, name="Permit Review", order=1):
    """Attach a process_module tile under the admin group, nesting one
    process_requirement child per RequirementRow."""
    builder.prune_blank_tiles(admin, pa_groups.PROCESS_MODULE, pa.MODULE_NAME)
    module = builder.append_blank_tile_for_group(
        admin,
        pa_groups.PROCESS_MODULE,
        {
            pa.MODULE_NAME: builder.localized(name),
            pa.MODULE_ID: str(uuid4()),
            pa.MODULE_ORDER: order,
        },
    )
    builder.prune_blank_tiles(module, pa.PROCESS_REQUIREMENT)
    for row in rows:
        values = {pa.PROCESS_REQUIREMENT_ORDER: row.order}
        if row.requirement is not None:
            values[pa.PROCESS_REQUIREMENT] = row.requirement
        child = builder.append_blank_tile_for_group(
            module, pa.PROCESS_REQUIREMENT, values
        )
        if row.assignee is not None:
            child.aliased_data.ministry_assignee = row.assignee
    return module


def make_requirement(builder, key, satisfied=False, name="Outstanding"):
    """A plain process requirement with no sub-requirements."""
    return builder.make_process_requirement(
        {
            "id": f"REQ-{key}",
            "name": name,
            "due": "2026-03-01",
            "notes": "",
            "satisfied": satisfied,
            "sub_requirements": [],
        }
    )


def build_permit(
    builder,
    name,
    rows=(),
    submission_date="2026-01-01",
    filing_type=None,
    organization=None,
    related_permit=None,
    admin_values=None,
):
    """A permit_application carrying the tiles a dashboard card reads, with one
    process_module holding the given requirement rows. No rows drops the blank
    module tile, the shape an externally-created application has; no submission
    date leaves it unsubmitted, which the internal dashboard hides."""
    permit = builder.new_resource("permit_application")
    builder.append_blank_tile_for_group(
        permit,
        pa_groups.APPLICATION_IDENTIFICATION,
        {
            pa.PROJECT_NAME: builder.localized(name),
            pa.APPLICATION_ID: builder.localized(name),
            pa.FILING_TYPE: reference_value(
                "permit_application", pa.FILING_TYPE, filing_type
            ),
            pa.OWNING_ORGANIZATION: organization,
        },
    )
    if related_permit is not None:
        builder.append_blank_tile_for_group(
            permit,
            pa.RELATED_PERMIT,
            {pa.RELATED_PERMIT: related_permit, pa.IS_RELATED_PERMIT: True},
        )
    values = {
        pa.APPLICATION_PRIORITY_LEVEL: reference_value(
            "permit_application", pa.APPLICATION_PRIORITY_LEVEL
        ),
        **(admin_values or {}),
    }
    if submission_date:
        values[pa.APPLICATION_SUBMISSION_DATE] = submission_date
    admin = builder.append_blank_tile_for_group(
        permit, pa_groups.APPLICATION_ADMIN, values
    )
    if rows:
        attach_module(builder, admin, rows)
    else:
        builder.prune_blank_tiles(admin, pa_groups.PROCESS_MODULE, pa.MODULE_NAME)
    permit.save(**builder.save_kwargs)
    return permit
