"""Helpers for arches `string` datatype node values, shaped
{"<lang>": {"value": ..., "direction": ...}}."""


def localized_string(value):
    """The string from an i18n node value, taking the first language present;
    empty or missing values become ""."""
    if not value:
        return ""
    return next(iter(value.values()))["value"]
