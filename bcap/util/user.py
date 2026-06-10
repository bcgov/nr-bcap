"""Person-name helpers: joining name parts, and the Django auth User's display
name (distinct from Contributor resources, which ContributorService handles)."""


def full_name(*parts):
    """The given name parts joined by spaces, skipping blank/None ones."""
    return " ".join(part for part in parts if part)


def display_name(user):
    """The user's full name, falling back to username; "" if no user."""
    if not user:
        return ""
    return full_name(user.first_name, user.last_name) or user.username
