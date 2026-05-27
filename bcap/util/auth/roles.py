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
    PERMITTING_ARCHAEOLOGIST = "Permitting Archaeologist"
    SENIOR_ARCHAEOLOGIST = "Senior Archaeologist"
    PERMITTING_MANAGER = "Permitting Manager"
