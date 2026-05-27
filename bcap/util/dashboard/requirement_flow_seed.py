"""Seeds one Permit Application carrying the real-world process-requirement flow
(Recommend Referral, Recommend Decision, Decision Summary) with full
sub-requirement checklists, so the dashboard can be exercised against
production-shaped data. Reuses the demo builder; only the requirement specs
differ. Temporary developer aid; see the ``seed_permit_application`` command."""

from bcap.util.dashboard.dashboard_seed import DashboardDemoBuilder

_REQUIREMENTS = [
    {
        "id": "REQ-2026-001",
        "name": "Recommend Referral",
        "due": "2026-01-02",
        "notes": "",
        "satisfied": False,
        "process_requirement_order": 1,
        "sub_requirements": [
            {
                "name": "Recommendation",
                "description": "Specific considerations?",
                "sort_order": 1,
                "sub_satisfied": False,
            },
            {
                "name": "Consultation Period",
                "description": "XX Days (15, 30, etc.)",
                "sort_order": 2,
                "sub_satisfied": False,
            },
            {
                "name": "Has this application's priority changed?",
                "description": "Y/N upgraded/downgraded, why?",
                "sort_order": 3,
                "sub_satisfied": False,
            },
            {
                "name": "I have verified the CAD/Non-CAD results and false intersects",
                "description": "Y/N any changes to the results?",
                "sort_order": 4,
                "sub_satisfied": False,
            },
            {
                "name": "I have verified the HTG Marine and Snuneymuxw Marine overlap, if needed",
                "description": "Y/NA",
                "sort_order": 5,
                "sub_satisfied": False,
            },
            {
                "name": "Has the S4 notification letter been sent to the permit applicant?",
                "description": "Y/NA",
                "sort_order": 6,
                "sub_satisfied": False,
            },
            {
                "name": "Application date",
                "description": "XX each application revision must have unique date",
                "sort_order": 7,
                "sub_satisfied": False,
            },
            {
                "name": "Requested permit length or expiry date?",
                "description": "Y/N",
                "sort_order": 8,
                "sub_satisfied": False,
            },
            {
                "name": "Multi Assessment Permit?",
                "description": "Y/N",
                "sort_order": 9,
                "sub_satisfied": False,
            },
            {
                "name": "BC Energy Regulator related Permit?",
                "description": "Y/N",
                "sort_order": 10,
                "sub_satisfied": False,
            },
            {
                "name": "Concurrent Permit?",
                "description": "Application or permit number",
                "sort_order": 11,
                "sub_satisfied": False,
            },
            {
                "name": "First Nation file number",
                "description": "if known at this stage",
                "sort_order": 12,
                "sub_satisfied": False,
            },
            {
                "name": "First Nations to be removed from Interested Parties",
                "description": "list all parties to remove prior to referral",
                "sort_order": 13,
                "sub_satisfied": False,
            },
            {
                "name": "First Nations to be added to Interested Parties",
                "description": "list all parties to add prior to referral",
                "sort_order": 14,
                "sub_satisfied": False,
            },
            {
                "name": "Additional Referral Letter Text",
                "description": "additional text for referral letter if needed",
                "sort_order": 15,
                "sub_satisfied": False,
            },
            {
                "name": "Summarize Project",
                "description": "summary of project and methods",
                "sort_order": 16,
                "sub_satisfied": False,
            },
            {
                "name": "Were revisions requested prior to recommendation",
                "description": "Y/N if so, how many and what kind, has the revisions box been selected? Ensure the unique date for final application version corresponds to Details tab on APTS",
                "sort_order": 17,
                "sub_satisfied": False,
            },
            {
                "name": "Permit Holder Status",
                "description": "Good Standing, Overdue Obligations, Issuances on Hold, First Time Permit Holder?",
                "sort_order": 18,
                "sub_satisfied": False,
            },
            {
                "name": "Site form updates",
                "description": " Y/N Check SITELOG for any backlogged information that might need updating, Non-MAP permits only",
                "sort_order": 19,
                "sub_satisfied": False,
            },
            {
                "name": "Additional Recommended Conditions",
                "description": "Y/N e.g. Nisga'a, TNG, first time permit holder, etc.",
                "sort_order": 20,
                "sub_satisfied": False,
            },
            {
                "name": "Processing Notes:",
                "description": "Any other process notes for the Permitting Assistant here - additional attachments/document salutation?",
                "sort_order": 21,
                "sub_satisfied": False,
            },
        ],
    },
    {
        "id": "REQ-2026-002",
        "name": "Recommend Decision",
        "due": "2026-02-15",
        "notes": "",
        "satisfied": False,
        "process_requirement_order": 2,
        "sub_requirements": [
            {
                "name": "Recommendation",
                "description": "Issue/Reject/HOLD",
                "sort_order": 1,
                "sub_satisfied": False,
            },
            {
                "name": "Manager acting as Statutory Decision Maker",
                "description": "Y/N e.g., includes Decision Letters or authorizes alterations; potentially contentious",
                "sort_order": 2,
                "sub_satisfied": False,
            },
            {
                "name": "The methods described in the application and the consultation undertaken by the Province have been considered in my recommendation for decision.",
                "description": "Y/N",
                "sort_order": 3,
                "sub_satisfied": False,
            },
            {
                "name": "Has this application's priority changed",
                "description": "Y/N if upgraded/downgraded, why?",
                "sort_order": 4,
                "sub_satisfied": False,
            },
            {
                "name": "Has a HOLD been placed on this application",
                "description": "Y/N if yes, why?",
                "sort_order": 5,
                "sub_satisfied": False,
            },
            {
                "name": "Did you conduct the technical review of this application?",
                "description": "Y/N Add any more information that might be relevant - does it deviate from the usual approach?",
                "sort_order": 6,
                "sub_satisfied": False,
            },
            {
                "name": "Did you conduct the consultation review for this application",
                "description": "Y/N",
                "sort_order": 7,
                "sub_satisfied": False,
            },
            {
                "name": "FN File numbers",
                "description": "",
                "sort_order": 8,
                "sub_satisfied": False,
            },
            {
                "name": "Concerns of Note",
                "description": "Note Nation and describe concerns",
                "sort_order": 9,
                "sub_satisfied": False,
            },
            {
                "name": "See Consultation Summary for consultation record related to this application OR Summarize First Nation Comments",
                "description": "provide summary if only a few comments or refer to Consultation Summary Table",
                "sort_order": 10,
                "sub_satisfied": False,
            },
            {
                "name": "Number of Decision Letters",
                "description": "List FNs with DLs and which application the DL is located",
                "sort_order": 11,
                "sub_satisfied": False,
            },
            {
                "name": "SERs are up to date, and include",
                "description": "check all SERs are up to date and list FNs-version numbers",
                "sort_order": 12,
                "sub_satisfied": False,
            },
            {
                "name": "Decision Considerations",
                "description": "e.g., S4 sites; related to contravention?",
                "sort_order": 13,
                "sub_satisfied": False,
            },
            {
                "name": "Summarize Project",
                "description": "provide summary of project and methods and indicate whether there were revisions",
                "sort_order": 14,
                "sub_satisfied": False,
            },
            {
                "name": "Permit Holder Status",
                "description": "Good Standing, Overdue Obligations, Issuances on Hold, First Time Permit Holder?",
                "sort_order": 15,
                "sub_satisfied": False,
            },
            {
                "name": "Recommending additional conditions?",
                "description": "Y/N If yes, describe",
                "sort_order": 16,
                "sub_satisfied": False,
            },
            {
                "name": "Repository acceptance confirmed",
                "description": "Y/N",
                "sort_order": 17,
                "sub_satisfied": False,
            },
            {
                "name": "Processing Notes",
                "description": "Any other process notes for the Permitting Assistant here - additional attachments/document salutation?",
                "sort_order": 18,
                "sub_satisfied": False,
            },
        ],
    },
    {
        "id": "REQ-2026-003",
        "name": "Decision Summary",
        "due": "2026-03-30",
        "notes": "",
        "satisfied": False,
        "process_requirement_order": 3,
        "sub_requirements": [
            {
                "name": "Decision rendered",
                "description": "Authorize permit / reject application / hold on decision",
                "sort_order": 1,
                "sub_satisfied": False,
            },
            {
                "name": "Decision made by",
                "description": "SDM name",
                "sort_order": 2,
                "sub_satisfied": False,
            },
            {
                "name": "Date of decision",
                "description": "Auth. date",
                "sort_order": 3,
                "sub_satisfied": False,
            },
            {
                "name": "Relevant HCA section",
                "description": "s 12.2 / s 12.4 / other",
                "sort_order": 4,
                "sub_satisfied": False,
            },
            {
                "name": "Has the duty to consult been met",
                "description": "",
                "sort_order": 5,
                "sub_satisfied": False,
            },
            {
                "name": "Concerns with consultation",
                "description": "",
                "sort_order": 6,
                "sub_satisfied": False,
            },
            {
                "name": "Decision letters related to decision",
                "description": "",
                "sort_order": 7,
                "sub_satisfied": False,
            },
            {
                "name": "Were any previous decisions considered/referenced in the making of this decision",
                "description": "",
                "sort_order": 8,
                "sub_satisfied": False,
            },
            {
                "name": "Other considerations related to this decision",
                "description": "",
                "sort_order": 9,
                "sub_satisfied": False,
            },
            {
                "name": "Changes to conditions of the permit",
                "description": "",
                "sort_order": 10,
                "sub_satisfied": False,
            },
            {
                "name": "Changes to SME recommendations",
                "description": "",
                "sort_order": 11,
                "sub_satisfied": False,
            },
            {
                "name": "Processing Notes",
                "description": "e.g. additional documents for inclusion, concurrent issuances",
                "sort_order": 12,
                "sub_satisfied": False,
            },
        ],
    },
]


class RequirementFlowBuilder(DashboardDemoBuilder):
    """Build one permit carrying the full real-world requirement flow. Only the
    requirement specs differ from the demo builder; assignees, holders, and
    graph assembly are inherited."""

    _REQUIREMENTS = _REQUIREMENTS
    _SEED_UNASSIGNED_PERMIT = False
