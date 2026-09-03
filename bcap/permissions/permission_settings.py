"""Instance-level permission defaults, read by arches as PERMISSION_DEFAULTS.

One entry per graph: under default deny a user reaches nothing it does not own
without a grant here. The applier in the permission framework reads the same
entries to grant the matching nodegroup perms, so this is the only place a role
is given access to a graph.
"""

from functools import lru_cache

from django.apps import apps
from django.utils.functional import lazy


@lru_cache(maxsize=None)
def _group_id(name):
    """The named group's id. Ids differ between databases, so they cannot be
    written down here. Only hits are cached, so a resolve that runs before the
    group's seeding migration retries rather than sticking for the process."""
    return apps.get_model("auth", "Group").objects.get(name=name).id


GroupId = lazy(_group_id, int)

# Instance-level permission defaults, one entry per graph. Under default deny a
# user reaches nothing it does not own without a grant here.
#
# What the entries below add up to, written R(ead) W(rite) A(dd) D(elete).
# Archaeology Branch holds RWAD on every graph and is left out of the rows.
#
#   permit work            Permit Reviewer/Decider/SDM RWAD, Inventory
#   (permit_application,   Reviewer/Manager RWAD, Resource Editor RWA,
#   alteration,            Resource Reviewer RW, Resource Exporter R
#   inspection,
#   investigation,
#   information_request,
#   notice_of_project_intent,
#   bcap_message,
#   document_submission,
#   contributor)
#
#   process_requirement    Permit Decider/SDM RWAD, Inventory Manager RWAD,
#                          Resource Editor RWA, Permit Reviewer RW, Resource
#                          Reviewer RW, Inventory Reviewer RW,
#                          Resource Exporter R
#
#   inventory              Inventory Manager RWAD, Inventory Reviewer RW
#   (archaeological_site,
#   site_visit,
#   site_submission)
#
#   hca_permit             Inventory Manager RWAD, Permit Decider/SDM RWAD,
#                          Inventory Reviewer RW, Permit Reviewer RW
#
#   publication,           Resource Editor RWA, Resource Reviewer R,
#   repository             Resource Exporter R
#
#   legislative_act,       Resource Editor/Reviewer/Exporter R
#   local_government
#
#   workflow_drafts        every internal group RWAD
#
#   branch only            no other group: project_sandbox,
#                          hria_discontinued_data, lg_person
#
# Permit Manager appears on workflow_drafts alone, so it reads no permit.

ARCHAEOLOGY_BRANCH_GROUP_ID = GroupId("Archaeology Branch")
INVENTORY_MANAGER_GROUP_ID = GroupId("Inventory Manager")
INVENTORY_REVIEWER_GROUP_ID = GroupId("Inventory Reviewer")
PERMIT_DECIDER_GROUP_ID = GroupId("Permit Decider")
PERMIT_MANAGER_GROUP_ID = GroupId("Permit Manager")
PERMIT_REVIEWER_GROUP_ID = GroupId("Permit Reviewer")
PERMIT_SDM_GROUP_ID = GroupId("Permit SDM")
RESOURCE_EDITOR_GROUP_ID = GroupId("Resource Editor")
RESOURCE_EXPORTER_GROUP_ID = GroupId("Resource Exporter")
RESOURCE_REVIEWER_GROUP_ID = GroupId("Resource Reviewer")

PERMISSION_DEFAULTS = {
    "cef9c510-e3e6-4057-ac08-89ad926180b4": [  # archaeological_site
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_MANAGER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
    ],
    "2da1c15f-1ab6-4122-9dbc-d10da693ac79": [  # site_visit
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_MANAGER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
    ],
    "52dd40f2-1dee-45d2-b72c-234c8cbb5418": [  # legislative_act
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EDITOR_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EXPORTER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
    ],
    "aacf8bb6-3f6e-46d9-a551-b0749d7efffc": [  # local_government
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EDITOR_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EXPORTER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
    ],
    "4e69d0a9-7af2-473f-929f-71d462ea32d1": [  # site_submission
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_MANAGER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
    ],
    "c3923080-d21e-42d7-b8f1-637b9d0ab63c": [  # project_sandbox
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
    ],
    "19806d98-8200-45b4-9f5d-9f07d9a9aaa1": [  # hria_discontinued_data
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
    ],
    "412444dd-b13f-4289-9f04-5c7f1878ad4e": [  # lg_person
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
    ],
    # Submitter is deliberately absent from every graph. External users reach
    # their own work through ownership, which passes before any grant is
    # consulted; a grant here would be graph-wide and let one submitter read and
    # edit another's.
    "fb6a3fbf-070d-43ae-b52c-0d1bfb78f206": [  # workflow_drafts
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EDITOR_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EXPORTER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_DECIDER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_SDM_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_MANAGER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_MANAGER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
    ],
    "5c900e2b-257c-4af3-b67f-b5caf3850f71": [  # permit_application
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EDITOR_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EXPORTER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
        {
            "id": PERMIT_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_DECIDER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_SDM_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_MANAGER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
    ],
    "b2901f47-bdfc-47bb-b212-3132b96efb0a": [  # alteration
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EDITOR_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EXPORTER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
        {
            "id": PERMIT_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_DECIDER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_SDM_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_MANAGER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
    ],
    "87968032-6faa-481b-a47c-30f9747acd52": [  # inspection
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EDITOR_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EXPORTER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
        {
            "id": PERMIT_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_DECIDER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_SDM_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_MANAGER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
    ],
    "febca6ba-2a51-494f-9809-c54e2dd42fc3": [  # investigation
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EDITOR_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EXPORTER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
        {
            "id": PERMIT_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_DECIDER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_SDM_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_MANAGER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
    ],
    "d4f514eb-bdc6-4f68-9c27-92883e1d4e7d": [  # information_request
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EDITOR_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EXPORTER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
        {
            "id": PERMIT_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_DECIDER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_SDM_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_MANAGER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
    ],
    "6ca13de7-f5b3-4e38-a947-64eaf2a04b65": [  # notice_of_project_intent
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EDITOR_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EXPORTER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
        {
            "id": PERMIT_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_DECIDER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_SDM_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_MANAGER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
    ],
    "fef4e675-e4c8-4bea-9e8a-cb30c3978bef": [  # bcap_message
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EDITOR_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EXPORTER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
        {
            "id": PERMIT_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_DECIDER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_SDM_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_MANAGER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
    ],
    "0e74b1fa-1da4-4f17-9e65-dd79fbc96313": [  # process_requirement
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EDITOR_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EXPORTER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
        {
            "id": PERMIT_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
        {
            "id": PERMIT_DECIDER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_SDM_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_MANAGER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
    ],
    "010b893e-c9d2-4dfe-b5d1-837c49c2bb9a": [  # document_submission
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EDITOR_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EXPORTER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
        {
            "id": PERMIT_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_DECIDER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_SDM_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_MANAGER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
    ],
    "f4b391f1-79d1-4886-ab2d-d72a197a9f21": [  # hca_permit
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_MANAGER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
        {
            "id": PERMIT_DECIDER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_SDM_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
    ],
    "605b0bbc-8661-4cf2-b340-df743a8c5f89": [  # contributor
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EDITOR_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EXPORTER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
        {
            "id": PERMIT_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_DECIDER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": PERMIT_SDM_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": INVENTORY_MANAGER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
    ],
    "3caf329f-b8f7-11e6-84a5-026d961c88e6": [  # publication
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EDITOR_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EXPORTER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
    ],
    "3e6a2880-14d4-11ec-9df0-5254008afee6": [  # repository
        {
            "id": ARCHAEOLOGY_BRANCH_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
                "delete_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_REVIEWER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EDITOR_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
                "change_resourceinstance",
                "add_resourceinstance",
            ],
        },
        {
            "id": RESOURCE_EXPORTER_GROUP_ID,
            "type": "group",
            "permissions": [
                "view_resourceinstance",
            ],
        },
    ],
}
