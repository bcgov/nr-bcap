"""Instance-level permission defaults, read by arches as PERMISSION_DEFAULTS.

Archaeology Branch reaches every graph. Submitter is granted the graphs an
applicant files: a permit application, everything hanging off one, and the
drafts on the way there. The grant is graph-wide, so the permission framework
narrows it per resource to the permits and drafts that applicant reaches.
"""

from django.utils.functional import lazy

from bcap.permissions.groups import Groups, group_id

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

PERMISSION_DEFAULTS = {
    # archaeological_site: the site inventory: staff record it, an applicant
    # never files one
    "cef9c510-e3e6-4057-ac08-89ad926180b4": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
    ],
    # site_visit: a visit to an inventoried site, recorded by staff
    "2da1c15f-1ab6-4122-9dbc-d10da693ac79": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
    ],
    # site_submission: a proposed change to the inventory, worked by staff
    "4e69d0a9-7af2-473f-929f-71d462ea32d1": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
    ],
    # legislative_act: reference data behind the inventory
    "52dd40f2-1dee-45d2-b72c-234c8cbb5418": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
    ],
    # local_government: reference data: the governments a site or permit falls
    # under
    "aacf8bb6-3f6e-46d9-a551-b0749d7efffc": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
    ],
    # lg_person: the contacts on a local government
    "412444dd-b13f-4289-9f04-5c7f1878ad4e": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
    ],
    # project_sandbox: staff scratch space
    "c3923080-d21e-42d7-b8f1-637b9d0ab63c": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
    ],
    # hria_discontinued_data: retired HRIA records, kept for staff lookup
    "19806d98-8200-45b4-9f5d-9f07d9a9aaa1": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
    ],
    # hca_permit: the issued permit, written by staff once a decision is made
    "f4b391f1-79d1-4886-ab2d-d72a197a9f21": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
    ],
    # publication: reference data on the reports the inventory cites
    "3caf329f-b8f7-11e6-84a5-026d961c88e6": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
    ],
    # repository: reference data on where artifacts are held
    "3e6a2880-14d4-11ec-9df0-5254008afee6": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
    ],
    # workflow_drafts: an applicant's unsubmitted work, and staff filling one in
    # for them
    "fb6a3fbf-070d-43ae-b52c-0d1bfb78f206": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
        {
            "id": SUBMITTER_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
    ],
    # permit_application: the applicant's filing, and the staff review of it
    "5c900e2b-257c-4af3-b67f-b5caf3850f71": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
        {
            "id": SUBMITTER_GROUP_ID,
            "type": "group",
            "permissions": APPLICANT_ACCESS,
        },
    ],
    # alteration: a permit type's own resource, filed as part of an application
    "b2901f47-bdfc-47bb-b212-3132b96efb0a": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
        {
            "id": SUBMITTER_GROUP_ID,
            "type": "group",
            "permissions": APPLICANT_ACCESS,
        },
    ],
    # inspection: a permit type's own resource, filed as part of an application
    "87968032-6faa-481b-a47c-30f9747acd52": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
        {
            "id": SUBMITTER_GROUP_ID,
            "type": "group",
            "permissions": APPLICANT_ACCESS,
        },
    ],
    # investigation: a permit type's own resource, filed as part of an
    # application
    "febca6ba-2a51-494f-9809-c54e2dd42fc3": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
        {
            "id": SUBMITTER_GROUP_ID,
            "type": "group",
            "permissions": APPLICANT_ACCESS,
        },
    ],
    # information_request: an applicant's request, answered by staff
    "d4f514eb-bdc6-4f68-9c27-92883e1d4e7d": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
        {
            "id": SUBMITTER_GROUP_ID,
            "type": "group",
            "permissions": APPLICANT_ACCESS,
        },
    ],
    # notice_of_project_intent: an applicant's notice ahead of a permit
    "6ca13de7-f5b3-4e38-a947-64eaf2a04b65": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
        {
            "id": SUBMITTER_GROUP_ID,
            "type": "group",
            "permissions": APPLICANT_ACCESS,
        },
    ],
    # bcap_message: the correspondence between an applicant and staff
    "fef4e675-e4c8-4bea-9e8a-cb30c3978bef": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
        {
            "id": SUBMITTER_GROUP_ID,
            "type": "group",
            "permissions": APPLICANT_ACCESS,
        },
    ],
    # process_requirement: the checklist on an application: staff set it, an
    # applicant answers it
    "0e74b1fa-1da4-4f17-9e65-dd79fbc96313": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
        {
            "id": SUBMITTER_GROUP_ID,
            "type": "group",
            "permissions": APPLICANT_ACCESS,
        },
    ],
    # document_submission: the files an applicant attaches to a requirement
    "010b893e-c9d2-4dfe-b5d1-837c49c2bb9a": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
        {
            "id": SUBMITTER_GROUP_ID,
            "type": "group",
            "permissions": APPLICANT_ACCESS,
        },
    ],
    # contributor: the person or company behind an account, edited from either
    # side
    "605b0bbc-8661-4cf2-b340-df743a8c5f89": [
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": FULL_ACCESS,
        },
        {
            "id": SUBMITTER_GROUP_ID,
            "type": "group",
            "permissions": APPLICANT_ACCESS,
        },
    ],
}

# Graphs where an applicant's grant is narrowed to the permit or draft the
# resource hangs off. Belongs here when a permit points at it within two hops;
# everything else is left to the route's owner filter.
# This drives check_resource_instance_permissions.
PERMIT_SCOPED_GRAPHS = frozenset(
    {
        "5c900e2b-257c-4af3-b67f-b5caf3850f71",  # permit_application
        "fb6a3fbf-070d-43ae-b52c-0d1bfb78f206",  # workflow_drafts
        "0e74b1fa-1da4-4f17-9e65-dd79fbc96313",  # process_requirement
        "fef4e675-e4c8-4bea-9e8a-cb30c3978bef",  # bcap_message
        "b2901f47-bdfc-47bb-b212-3132b96efb0a",  # alteration
        "87968032-6faa-481b-a47c-30f9747acd52",  # inspection
        "febca6ba-2a51-494f-9809-c54e2dd42fc3",  # investigation
        "010b893e-c9d2-4dfe-b5d1-837c49c2bb9a",  # document_submission
        "6ca13de7-f5b3-4e38-a947-64eaf2a04b65",  # notice_of_project_intent
        "d4f514eb-bdc6-4f68-9c27-92883e1d4e7d",  # information_request
    }
)
