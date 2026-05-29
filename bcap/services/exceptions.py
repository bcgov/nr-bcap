"""Domain exceptions raised by services. HTTP-agnostic -- views catch them and
re-raise as the appropriate response (e.g. StaleReference -> 404)."""


class StaleReference(Exception):
    """A request referenced resource state that no longer exists -- it was
    likely changed or deleted since the client loaded it."""
