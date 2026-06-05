"""Small, reusable queryset helpers."""


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
