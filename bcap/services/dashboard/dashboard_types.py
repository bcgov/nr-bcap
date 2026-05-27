from dataclasses import MISSING, dataclass, field


def constrained(default, **serializer_kwargs):
    """A dataclass field that carries extra validation options (such as a
    minimum or maximum value) through to the generated serializer field."""
    return field(default=default, metadata={"serializer_kwargs": serializer_kwargs})


def described(help_text, default=MISSING, **serializer_kwargs):
    """A dataclass field whose help_text passes through to the generated
    serializer field, so it becomes that field's description in the OpenAPI
    spec. Omit `default` for a required field."""
    metadata = {"serializer_kwargs": {"help_text": help_text, **serializer_kwargs}}
    if default is MISSING:
        return field(metadata=metadata)
    return field(default=default, metadata=metadata)


@dataclass
class DashboardFilter:
    """The request parameters that filter and page the dashboard cards."""

    contributor_id: str | None = None
    status: str | None = None
    limit: int = constrained(50, min_value=1, max_value=100)
    page: int = constrained(1, min_value=1)
    order_by: str | None = None


@dataclass
class DashboardCard:
    """Response structure for the internal dashboard, and the single source of
    truth for the card's shape -- the response serializer derives its fields
    from this dataclass."""

    id: str = described(
        "Permit application resourceinstanceid; the card's drill-in GUID."
    )
    requirement_name: str = described(
        "Name of the chosen (first unsatisfied) process requirement.", ""
    )
    requirement_due_date: str = described(
        "Process due date of the chosen requirement.", ""
    )
    project_name: str = described("Permit application's project name.", "")
    application_id: str = described("Permit application's application ID.", "")
    industrial_sector: str = described(
        "Permit application's industrial sector (reference label).", ""
    )
    permit_number: str = described("Permit number of the related HCA Permit.", "")
    permit_holder: str = described(
        "Permit holder name(s) on the related HCA Permit (Contributor).", ""
    )
    project_officer: str = described(
        "Project officer on the permit's application_admin group (Contributor name).",
        "",
    )
    assessment_notes: str = described("Assessment notes on the chosen requirement.", "")
    ministry_assignee_name: str = described(
        "Ministry assignee on the chosen requirement tile (Contributor name).", ""
    )
    ministry_assignee_change_date: str = described(
        "Edit-log date the chosen tile's ministry_assignee last changed.", ""
    )
    requirement_route: str = described(
        "Resourceinstanceid of the chosen Process Requirement; the drill-in target.",
        "",
    )
    urgency: int = described(
        "Relative urgency from the target completion date and the current date.", 0
    )
    priority_level: str = described(
        "Permit application's priority level (reference label).", ""
    )


@dataclass
class DashboardPage:
    """A page of dashboard cards plus the paging metadata the client needs to
    render page controls: the total matching the query (before paging) and the
    page/limit that produced these results."""

    count: int = 0
    page: int = 1
    limit: int = 0
    results: list[DashboardCard] = field(default_factory=list)
