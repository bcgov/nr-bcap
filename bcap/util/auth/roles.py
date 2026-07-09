# Canonical role names, used to gate dashboard data by the user's groups.
#
# These strings must match the Django ``auth.Group`` names exactly, since the
# current authorization check is group-membership based (see
# ``DashboardService.get_cards``):
#
#   group_names = [g.name for g in user.groups.all()]
#   if Roles.PERMITTING_ARCHAEOLOGIST in group_names:
#       ...
#
# TODO: This is a stub. Role-to-permission mapping is likely to outgrow plain
# group-name string matching (e.g. per-object access: an archaeologist should
# only see their own permits, a manager their team's). When that happens,
# consider moving to django-guardian for object-level permissions
# (https://django-guardian.readthedocs.io/) and replacing the group-name
# checks with permission checks (e.g. ``user.has_perm("view_permit", permit)``).


class Roles:
    ARCHAEOLOGY_BRANCH = "Archaeology Branch"
    RESOURCE_EDITOR = "Resource Editor"


# Ministry staff roles. A user without any of these (and not a superuser) is an
# external applicant. Extend this set if more internal groups are added.
INTERNAL_ROLES = {
    Roles.ARCHAEOLOGY_BRANCH,
    Roles.RESOURCE_EDITOR,
}


def is_internal_user(user):
    """True if the user is ministry staff (a superuser or holds an internal
    role); everyone else is treated as an external applicant."""
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.groups.filter(name__in=INTERNAL_ROLES).exists()
