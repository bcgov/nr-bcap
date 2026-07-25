# Canonical group names, used to gate dashboard data by the user's groups.
#
# These strings must match the Django auth.Group names exactly, since the
# current authorization check is group-membership based: read the names off
# user.groups and compare.
#
# TODO: This is a stub. Group-to-permission mapping is likely to outgrow plain
# group-name string matching (e.g. per-object access: an archaeologist should
# only see their own permits, a manager their team's). When that happens,
# consider moving to django-guardian for object-level permissions
# (https://django-guardian.readthedocs.io/) and replacing the group-name
# checks with permission checks (e.g. user.has_perm("view_permit", permit)).

from django.contrib.auth import get_user_model


class Groups:
    ARCHAEOLOGY_BRANCH = "Archaeology Branch"
    RESOURCE_EDITOR = "Resource Editor"


# Ministry staff groups. A user without any of these (and not a superuser) is an
# external applicant. Extend this set if more internal groups are added.
INTERNAL_GROUPS = {
    Groups.ARCHAEOLOGY_BRANCH,
    Groups.RESOURCE_EDITOR,
}


def is_internal_user(user):
    """True if the user is ministry staff (a superuser or holds an internal
    group); everyone else is treated as an external applicant."""
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.groups.filter(name__in=INTERNAL_GROUPS).exists()


def is_internal_username(username):
    """True if a user with this username exists and is ministry staff."""
    if not username:
        return False
    user = get_user_model().objects.filter(username=username).first()
    return bool(user and is_internal_user(user))
