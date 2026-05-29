"""Helpers for arches `string` datatype values, stored localized as
{language: {"value": ..., "direction": ...}}."""


def to_text(value):
    """Plain text from a string node value (localized dict or bare string)."""
    if not value:
        return ""
    if isinstance(value, str):
        return value
    return next(iter(value.values())).get("value", "")
