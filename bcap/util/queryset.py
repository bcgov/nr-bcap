"""Small, reusable queryset helpers."""

from functools import reduce


def filter_or_empty(queryset, **lookups):
    """Like ``filter``, but return nothing when any lookup value is empty, so a
    missing id excludes everything instead of matching on ``None``."""
    if not all(lookups.values()):
        return queryset.none()
    return queryset.filter(**lookups)


def first_pk(queryset):
    """The first row's primary key as a string, or None if there is no row."""
    instance = queryset.first()
    return str(instance.pk) if instance else None


def deep_get(obj, *keys):

    return reduce(
        lambda d, k: d.get(k) if isinstance(d, dict) else None,
        keys,
        obj,
    )
