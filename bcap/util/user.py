"""Person-name helpers: joining name parts, and the Django auth User's display
name (distinct from Contributor resources, which ContributorService handles)."""

from django.contrib.auth import get_user_model


def full_name(*parts):
    """The given name parts joined by spaces, skipping blank/None ones."""
    return " ".join(part for part in parts if part)


def last_first(first, last):
    """ "Last, First" display name, skipping a blank part (so an org with only a
    single name reads as just that name)."""
    return ", ".join(part for part in (last, first) if part)


def display_name(user):
    """The user's full name, blank when they have none. Never the username: for
    a BCeID account that is a login identifier, and these names are shown to
    other applicants."""
    if not user:
        return ""
    return full_name(user.first_name, user.last_name) or "Unknown"


def user_log_id(username):
    """A user's id for log lines, so a username (a credential) stays out of logs."""
    return (
        get_user_model()
        .objects.filter(username=username)
        .values_list("id", flat=True)
        .first()
    )
