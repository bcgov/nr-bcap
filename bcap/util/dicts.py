"""Small, reusable dict helpers."""

from functools import reduce


def kebab_case_keys(data):
    """The same dict with snake_case keys written as kebab-case."""
    return {key.replace("_", "-"): value for key, value in data.items()}


def deep_get(obj, *keys):
    """Walk nested dicts by key, returning None if any level is missing or not a
    dict."""
    return reduce(
        lambda d, k: d.get(k) if isinstance(d, dict) else None,
        keys,
        obj,
    )
