"""Helpers for date values."""


def to_iso(value):
    """A date as 'YYYY-MM-DD', or None for a falsy value."""
    return value.isoformat() if value else None


def to_long(value):
    """A date/datetime in long form, e.g. 'Monday, 15 January 2026'."""
    return value.strftime("%A, %d %B %Y")
