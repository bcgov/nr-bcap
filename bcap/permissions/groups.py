"""Canonical group (role) names, matching the Group rows seeded in the DB.

Referenced by the permission policy, the route gates, and tests. Keep these in
sync with the actual group names; a typo silently denies access rather than
erroring.

Archaeology Branch is the one group that marks a user as ministry staff. The
others authorize functions within the system (who may decide a permit, who may
add a multi-permit) and grant no data access on their own.
"""

from functools import lru_cache

from django.apps import apps
from django.contrib.auth import get_user_model


class Groups:
    ARCHAEOLOGY_BRANCH = "Archaeology Branch"
    RESOURCE_EDITOR = "Resource Editor"
    RESOURCE_REVIEWER = "Resource Reviewer"
    RESOURCE_EXPORTER = "Resource Exporter"
    PERMIT_REVIEWER = "Permit Reviewer"
    PERMIT_DECIDER = "Permit Decider"
    PERMIT_SDM = "Permit SDM"  # Statutory Decision Maker
    PERMIT_MANAGER = "Permit Manager"
    MPP_SUBMITTER = "MPP Submitter"  # Allows special group to add multi permit
    INVENTORY_REVIEWER = "Inventory Reviewer"
    INVENTORY_MANAGER = "Inventory Manager"
    SUBMITTER = "Submitter"  # External
    GUEST = "Guest"  # mapped to anonymous


# Role groups an admin can grant an invited user. External applicants always
# get just the Submitter group.
SELF_MANAGE_ROLE_GROUPS = [
    Groups.PERMIT_REVIEWER,
    Groups.PERMIT_SDM,
    Groups.PERMIT_MANAGER,
    Groups.INVENTORY_REVIEWER,
    Groups.INVENTORY_MANAGER,
    Groups.SUBMITTER,
]


@lru_cache(maxsize=None)
def group_id(name):
    """The named group's id. Ids differ between databases, so they cannot be
    written down in a setting. Only hits are cached, so a resolve that runs
    before the group's seeding migration retries rather than sticking for the
    process."""
    return apps.get_model("auth", "Group").objects.get(name=name).id


def is_internal_user(user):
    """True if the user is ministry staff (a superuser or in Archaeology
    Branch); everyone else is treated as an external applicant."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=Groups.ARCHAEOLOGY_BRANCH).exists()


def is_internal_username(username):
    """True if a user with this username exists and is ministry staff."""
    if not username:
        return False
    user = get_user_model().objects.filter(username=username).first()
    return bool(user and is_internal_user(user))
