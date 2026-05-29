"""Shared sentinel values."""


class _Unchanged:
    """A 'not provided' marker, distinct from None, for partial updates where
    None is a meaningful value (e.g. clearing a field)."""

    def __repr__(self):
        return "UNCHANGED"


UNCHANGED = _Unchanged()
