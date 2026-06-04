from django.db.models import TextChoices


class DashboardStatus(TextChoices):
    """Assignment-status filter for the dashboard, keyed on the active
    requirement's ministry_assignee. The labels feed the serializer's
    ChoiceField, so they surface as the status enum in the OpenAPI spec."""

    UNASSIGNED = "UNASSIGNED", "Unassigned"
    ASSIGNED_TO_ME = "ASSIGNED_TO_ME", "Assigned to me"
    ASSIGNED_TO_ASSOCIATED_COMPANIES = (
        "ASSIGNED_TO_ASSOCIATED_COMPANIES",
        "Assigned to associated companies",
    )
