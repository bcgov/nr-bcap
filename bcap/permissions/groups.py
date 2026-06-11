"""Canonical group (role) names, matching the Group rows seeded in the DB.

Referenced by the permission policy, the route gates, and tests. Keep these in
sync with the actual group names; a typo silently denies access rather than
erroring.
"""


class Groups:
    ARCHAEOLOGY_BRANCH = "Archaeology Branch"
    RESOURCE_EDITOR = "Resource Editor"
    RESOURCE_REVIEWER = "Resource Reviewer"
    RESOURCE_EXPORTER = "Resource Exporter"
    PERMIT_REVIEWER = "Permit Reviewer"
    PERMIT_DECIDER = "Permit Decider"
    INVENTORY_REVIEWER = "Inventory Reviewer"
    INVENTORY_MANAGER = "Inventory Manager"
    SUBMITTER = "Submitter"  # External
    GUEST = "Guest"  # mapped to anonymous
