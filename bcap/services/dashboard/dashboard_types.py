from dataclasses import MISSING, dataclass, field

from django.db.models import TextChoices

from arches_querysets.models import TileTree


class InternalDashboardStatus(TextChoices):
    """Assignment-status filter for the internal (ministry) dashboard, keyed on
    the active requirement's ministry_assignee. The labels feed the serializer's
    ChoiceField, so they surface as the status enum in the OpenAPI spec.

    No status (the parameter omitted) means ALL results -- the filter is not
    applied."""

    UNASSIGNED = "UNASSIGNED", "Unassigned"
    ASSIGNED_TO_ME = "ASSIGNED_TO_ME", "Assigned to me"


class ExternalDashboardStatus(TextChoices):
    """Scope filter for the external (applicant) dashboard: the user's drafts,
    their own submitted applications, or those of their associated companies.

    Scoped on created-by (principaluser) for now; the associated-companies match
    may move to an applicant field on the application later.
    """

    DRAFTS = "DRAFTS", "Drafts"
    CREATED_BY_ME = "CREATED_BY_ME", "My Projects"
    CREATED_BY_ASSOCIATED_COMPANIES = (
        "CREATED_BY_ASSOCIATED_COMPANIES",
        "Created by associated companies",
    )


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

    status: str | None = None
    limit: int = constrained(50, min_value=1, max_value=100)
    page: int = constrained(1, min_value=1)


@dataclass
class ModuleProgress:
    """What a dashboard card says about a permit's modules: how far along it is
    and which module it is waiting on. The per-module list is deliberately not
    exposed -- a card only ever renders this summary."""

    current_module: str = described(
        "Name of the lowest-ordered module not yet completed, or empty once "
        "they are all done.",
        "",
    )
    completed: int = described("How many modules are marked completed.", 0)
    total: int = described("How many modules the permit has.", 0)


@dataclass
class InternalDashboardCard:
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
    application_number: str = described(
        'Permit application\'s human-readable application reference (e.g. "APP-1"); '
        "not a GUID. The application's GUID is the card's `id`.",
        "",
    )
    submission_type: str = described(
        "Permit application's filing type (reference label).", ""
    )
    industrial_sector: str = described(
        "Permit application's industrial sector (reference label).", ""
    )
    permit_id: str | None = described(
        "Resourceinstanceid of the related HCA Permit; its drill-in GUID.", None
    )
    permit_number: str = described("Permit number of the related HCA Permit.", "")
    permit_holder: str = described(
        "Permit holder name(s) on the related HCA Permit (Contributor).", ""
    )
    permit_holder_ids: list[str] = field(
        default_factory=list,
        metadata={
            "serializer_kwargs": {
                "help_text": "Resourceinstanceids of the permit holder Contributor(s); their drill-in GUIDs."
            }
        },
    )
    project_officer: str = described(
        "Project officer on the permit's application_admin group (Contributor name).",
        "",
    )
    project_officer_id: str | None = described(
        "Resourceinstanceid of the project officer Contributor; its drill-in GUID.",
        None,
    )
    assessment_notes: str = described("Assessment notes on the chosen requirement.", "")
    ministry_assignee_name: str = described(
        "Ministry assignee on the chosen requirement tile (Contributor name).", ""
    )
    ministry_assignee_id: str | None = described(
        "Resourceinstanceid of the ministry assignee Contributor; its drill-in GUID.",
        None,
    )
    ministry_assignee_change_date: str = described(
        "Edit-log date the chosen tile's ministry_assignee last changed.", ""
    )
    requirement_id: str = described(
        "Resourceinstanceid of the chosen Process Requirement; the drill-in target.",
        "",
    )
    urgency: int = described(
        "Relative urgency from the target completion date and the current date.", 0
    )
    priority_level: str = described(
        "Permit application's priority level (reference label).", ""
    )
    unread_messages: int = described(
        "Count of the permit's BCAP messages not yet read for the user or group.",
        0,
    )
    module_progress: ModuleProgress = field(default_factory=ModuleProgress)


@dataclass
class ExternalDashboardCard:
    """Response structure for the external (applicant) dashboard. A reduced
    InternalDashboardCard: the project officer, ministry assignee, and all personal
    information (contributor names) are dropped -- not needed, and not exposed
    to external users in this first cut."""

    id: str = described(
        "Permit application resourceinstanceid, or draft id when is_draft; the "
        "card's drill-in / resume GUID."
    )
    is_draft: bool = described(
        "True when this card is an unsubmitted draft rather than a saved "
        "application.",
        False,
    )
    graph_slug: str = described(
        "Graph the draft belongs to, so the client can resume and delete it "
        "against the right workflow; empty for saved applications.",
        "",
    )
    permit_application_id: str = described(
        "Resourceinstanceid of the permit application a module draft was "
        "started from; empty for an application draft or a saved application.",
        "",
    )
    status: str = described(
        "Applicant-facing workflow status, e.g. Permit Active, Under Review, "
        "Submit Documents, Submission Required.",
        "",
    )
    created_by_name: str = described(
        "Display name of the user who created the application (principaluser).", ""
    )
    created_date: str = described(
        "ISO timestamp the application was submitted (its createdtime), or the "
        "draft was created when is_draft.",
        "",
    )
    submission_date: str = described(
        "Permit application's submission date; empty for drafts.", ""
    )
    updated_date: str = described(
        "ISO timestamp of the last save; only drafts carry one.", ""
    )
    project_name: str = described("Permit application's project name.", "")
    application_number: str = described(
        "Permit application's human-readable application reference; not a GUID.", ""
    )
    submission_type: str = described(
        "Permit application's filing type (reference label).", ""
    )
    industrial_sector: str = described(
        "Permit application's industrial sector (reference label).", ""
    )
    permit_id: str | None = described(
        "Resourceinstanceid of the related HCA Permit; its drill-in GUID.", None
    )
    permit_number: str = described("Permit number of the related HCA Permit.", "")
    urgency: int = described(
        "Relative urgency from the target completion date and the current date.", 0
    )
    priority_level: str = described(
        "Permit application's priority level (reference label).", ""
    )
    unread_messages: int = described(
        "Count of the application's BCAP messages not yet read for the user or "
        "group.",
        0,
    )
    module_progress: ModuleProgress = field(default_factory=ModuleProgress)


@dataclass
class InternalDashboardPage:
    """A page of dashboard cards plus the paging metadata the client needs to
    render page controls: the total matching the query (before paging) and the
    page/limit that produced these results."""

    count: int = 0
    page: int = 1
    limit: int = 0
    results: list[InternalDashboardCard] = field(default_factory=list)


@dataclass
class ExternalDashboardPage:
    """A page of external dashboard cards plus paging metadata (see
    InternalDashboardPage)."""

    count: int = 0
    page: int = 1
    limit: int = 0
    results: list[ExternalDashboardCard] = field(default_factory=list)


@dataclass
class HcaPermit:
    """An HCA Permit related to a permit application."""

    number: str = ""
    holder_ids: list[str] = field(default_factory=list)


@dataclass
class ApplicationCore:
    """The permit-application fields both dashboards' cards share, read straight
    off the loaded resource tree."""

    project_name: str = ""
    application_number: str = ""
    submission_type: str = ""
    industrial_sector: str = ""
    priority_level: str = ""
    related_permit_id: str | None = None


@dataclass
class Requirement:
    """An unsatisfied process requirement as the card needs it, paired with the
    permit's process_requirement tile that points at it. The tile carries the
    ministry_assignee and the id the assignee edit-log date is keyed by."""

    name: str = ""
    due_date: str = ""
    route: str = ""
    notes: str = ""
    tile: TileTree | None = None


@dataclass
class InternalDashboardData:
    """The per-permit lookups a card is assembled from, keyed by permit/tile id."""

    chosen_by_permit: dict[str, Requirement | None]
    assignee_dates: dict[str, str]
    hca_permits: dict[str, HcaPermit]
    contributor_names: dict[str, str]
    unread_counts: dict[str, int]
