"""Request/response shape for the Process Requirement PATCH endpoint. One shape
serves both: on PATCH omitted fields are left unchanged; the response carries
the saved values plus the resource id."""

from dataclasses import dataclass
from datetime import date

from bcap.services.dashboard.dashboard_types import described
from bcap.util.sentinels import UNCHANGED


@dataclass
class SubRequirement:
    """A sub-requirement, matched to its tile by id."""

    id: str | None = described(
        "Sub-requirement tile id; omit to add a new sub-requirement.", None
    )
    name: str | None = described(
        "Sub-requirement name; required when adding one.", None
    )
    satisfied: bool | None = described("Whether it is satisfied.", None)
    assessment_notes: str | None = described(
        "Assessment notes.", None, allow_blank=True
    )
    sort_order: int | None = described(
        "Sort order; required when adding a new sub-requirement.", None
    )


@dataclass
class ProcessRequirement:
    """The process dates and sub-requirements of a Process Requirement. Edits
    the requirement in place (it is never created here); a sub-requirement
    without an id is added, and omitted fields are left unchanged."""

    id: str | None = described("Resource id (set on the response).", None)
    # Default UNCHANGED (not None) so an omitted date is distinguishable from an
    # explicit null: omitted -> left as is, null -> cleared.
    start_date: date | None = described(
        "Process start date PST (YYYY-MM-DD); null clears it.", UNCHANGED
    )
    due_date: date | None = described(
        "Process due date PST (YYYY-MM-DD); null clears it.", UNCHANGED
    )
    completion_date: date | None = described(
        "Process completion date PST (YYYY-MM-DD); null clears it.", UNCHANGED
    )
    sub_requirements: list[SubRequirement] | None = described(
        "Sub-requirements, in display order.", None
    )
