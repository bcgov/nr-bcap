"""Small, reusable queryset helpers."""


def filter_or_empty(queryset, **lookups):
    """Like ``filter``, but return nothing when any lookup value is empty, so a
    missing id excludes everything instead of matching on ``None``."""
    if not all(lookups.values()):
        return queryset.none()
    return queryset.filter(**lookups)
