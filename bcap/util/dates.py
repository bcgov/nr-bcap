"""Helpers for date values."""

from datetime import datetime


def parse_iso_or_set_value(value):
    """Normalize an ISO datetime (browser '...Z' or Arches space-separated) to the
    seconds offset string the date datatype stores; non-strings pass through."""
    if not isinstance(value, str):
        return value
    return datetime.fromisoformat(value).replace(microsecond=0).isoformat(sep=" ")


def to_iso(value):
    """A date as 'YYYY-MM-DD', or None for a falsy value."""
    return value.isoformat() if value else None


def to_long(value):
    """A date/datetime in long form, e.g. 'Monday, 15 January 2026'."""
    return value.strftime("%A, %d %B %Y")
