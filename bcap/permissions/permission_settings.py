"""Instance-level permission defaults, read by arches as PERMISSION_DEFAULTS.

Archaeology Branch reaches every graph. Submitter is granted the graphs an
applicant files: a permit application, everything hanging off one, and the
drafts on the way there. The grant is graph-wide, so the permission framework
narrows it per resource to the permits and drafts that applicant reaches.

One line per graph, so the policy reads down the page rather than being
assembled from thirty near-identical dicts.
"""

from django.utils.functional import lazy

from bcap.permissions.groups import Groups, group_id
from bcap.util.graph_ids import GraphIds

GroupId = lazy(group_id, int)

ARCHAEOLOGY_BRANCH_GROUP_ID = GroupId(Groups.ARCHAEOLOGY_BRANCH)
SUBMITTER_GROUP_ID = GroupId(Groups.SUBMITTER)

FULL_ACCESS = [
    "view_resourceinstance",
    "change_resourceinstance",
    "add_resourceinstance",
    "delete_resourceinstance",
]

# An applicant files and revises but never removes: a submitted resource is part
# of the record. Their own drafts are the exception, and get full access.
APPLICANT_ACCESS = [
    "view_resourceinstance",
    "change_resourceinstance",
    "add_resourceinstance",
]

STAFF = (ARCHAEOLOGY_BRANCH_GROUP_ID, FULL_ACCESS)
APPLICANT = (SUBMITTER_GROUP_ID, APPLICANT_ACCESS)
APPLICANT_OWNS = (SUBMITTER_GROUP_ID, FULL_ACCESS)


def grants(*roles):
    """A graph's entry: the dict arches expects, one per role granted."""
    return [
        {"id": group, "type": "group", "permissions": permissions}
        for group, permissions in roles
    ]


PERMISSION_DEFAULTS = {
    # The inventory and the reference data behind it: staff record it, an
    # applicant never files one.
    GraphIds.ARCHAEOLOGICAL_SITE: grants(STAFF),
    GraphIds.SITE_VISIT: grants(STAFF),
    GraphIds.SITE_SUBMISSION: grants(STAFF),
    GraphIds.LEGISLATIVE_ACT: grants(STAFF),
    GraphIds.LOCAL_GOVERNMENT: grants(STAFF),
    GraphIds.LG_PERSON: grants(STAFF),
    GraphIds.PROJECT_SANDBOX: grants(STAFF),
    GraphIds.HRIA_DISCONTINUED_DATA: grants(STAFF),
    GraphIds.PUBLICATION: grants(STAFF),
    GraphIds.REPOSITORY: grants(STAFF),
    # The issued permit, written by staff once a decision is made.
    GraphIds.HCA_PERMIT: grants(STAFF),
    # An applicant's unsubmitted work, and staff filling one in for them.
    GraphIds.WORKFLOW_DRAFTS: grants(STAFF, APPLICANT_OWNS),
    # The filing, the staff review of it, and everything hanging off one.
    GraphIds.PERMIT_APPLICATION: grants(STAFF, APPLICANT),
    GraphIds.ALTERATION: grants(STAFF, APPLICANT),
    GraphIds.INSPECTION: grants(STAFF, APPLICANT),
    GraphIds.INVESTIGATION: grants(STAFF, APPLICANT),
    GraphIds.INFORMATION_REQUEST: grants(STAFF, APPLICANT),
    GraphIds.NOTICE_OF_PROJECT_INTENT: grants(STAFF, APPLICANT),
    GraphIds.BCAP_MESSAGE: grants(STAFF, APPLICANT),
    GraphIds.PROCESS_REQUIREMENT: grants(STAFF, APPLICANT),
    GraphIds.DOCUMENT_SUBMISSION: grants(STAFF, APPLICANT),
    # The person or company behind an account, edited from either side.
    GraphIds.CONTRIBUTOR: grants(STAFF, APPLICANT),
}
