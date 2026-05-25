from dataclasses import dataclass, field


def constrained(default, **serializer_kwargs):
    """A dataclass field that carries extra validation options (such as a
    minimum or maximum value) through to the generated serializer field."""
    return field(default=default, metadata={"serializer_kwargs": serializer_kwargs})


@dataclass
class DashboardQuery:
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

    id: str
    cap_label: str = ""
    cap_date: str = ""
    body_title: str = ""
    body_subtitle1: str = ""
    body_subtitle2: str = ""
    body1: str = ""
    body2: str = ""
    body3: str = ""
    body4: str = ""
    body5: str = ""
    footer_name: str = ""
    footer_date: str = ""
    route: str = ""
    urgency: int = 0
    cap_priority: str = ""


@dataclass
class DashboardPage:
    """A page of dashboard cards plus the paging metadata the client needs to
    render page controls: the total matching the query (before paging) and the
    page/limit that produced these results."""

    count: int = 0
    page: int = 1
    limit: int = 0
    results: list[DashboardCard] = field(default_factory=list)
