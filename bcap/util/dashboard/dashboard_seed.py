"""Builds the dashboard demo graph -- a Permit Application linked to a Process
Requirement, an HCA Permit, and Contributors.

Shared by the dashboard service tests and the ``seed_dashboard_demo`` command,
and built through arches-querysets (via ``ResourceBuilder``) so it stays in sync
with how the service reads.
"""

from dataclasses import dataclass

from arches_querysets.models import ResourceTileTree

from bcap.util.dashboard.resource_builder import ResourceBuilder


@dataclass
class DashboardDemoData:
    permit: ResourceTileTree
    hca_permit: ResourceTileTree
    assignees: list[ResourceTileTree]
    holders: list[ResourceTileTree]
    process_requirements: list[ResourceTileTree]


class DashboardDemoBuilder(ResourceBuilder):
    """Create the demo graph and return the resources it produced.

    Builds a Permit Application with all three process requirements (the first
    fully satisfied, the rest still outstanding). The low-level resource builders
    it uses live in ``ResourceBuilder``.
    """

    _ASSIGNEE_NAMES = [
        ("Ada", "Lovelace"),
        ("Grace", "Hopper"),
        ("Alan", "Turing"),
    ]
    _HOLDER_NAMES = ["Acme Corp", "Globex"]

    _REQUIREMENTS = [
        {
            "id": "REQ-2026-001",
            "name": "Review",
            "due": "2026-01-02",
            "notes": "all sub-requirements complete",
            "satisfied": True,
            "process_requirement_order": 1,
            "sub_requirements": [
                {
                    "name": "Submit application forms",
                    "sort_order": 1,
                    "description": "",
                    "sub_satisfied": True,
                },
                {
                    "name": "Schedule site inspection",
                    "sort_order": 2,
                    "description": "",
                    "sub_satisfied": True,
                },
                {
                    "name": "Final review",
                    "sort_order": 3,
                    "description": "",
                    "sub_satisfied": True,
                },
            ],
        },
        {
            "id": "REQ-2026-002",
            "name": "Field Assessment",
            "due": "2026-02-15",
            "notes": "awaiting site access",
            "satisfied": False,
            "process_requirement_order": 2,
            "sub_requirements": [
                {
                    "name": "Submit application forms",
                    "sort_order": 1,
                    "description": "",
                    "sub_satisfied": False,
                },
                {
                    "name": "Schedule site inspection",
                    "sort_order": 2,
                    "description": "",
                    "sub_satisfied": True,
                },
                {
                    "name": "Final review",
                    "sort_order": 3,
                    "description": "",
                    "sub_satisfied": False,
                },
            ],
        },
        {
            "id": "REQ-2026-003",
            "name": "Final Sign-off",
            "due": "2026-03-30",
            "notes": "pending manager approval",
            "satisfied": False,
            "process_requirement_order": 3,
            "sub_requirements": [
                {
                    "name": "Submit application forms",
                    "sort_order": 1,
                    "description": "",
                    "sub_satisfied": False,
                },
                {
                    "name": "Schedule site inspection",
                    "sort_order": 2,
                    "description": "",
                    "sub_satisfied": False,
                },
                {
                    "name": "Final review",
                    "sort_order": 3,
                    "description": "",
                    "sub_satisfied": True,
                },
            ],
        },
    ]

    def build(self):
        """Create the demo graph and return the resources it produced."""
        contributor_type = self.reference_value("contributor", "contributor_type")

        assignees = [
            self.make_contributor(contributor_type, first, last)
            for first, last in self._ASSIGNEE_NAMES
        ]
        holders = [
            self.make_contributor(contributor_type, None, org)
            for org in self._HOLDER_NAMES
        ]

        hca_permit = self.new_resource("hca_permit")
        self.append_blank_tile_for_group(
            hca_permit,
            "permit_identification",
            {
                "permit_number": "HCA-001",
                "permit_holder": holders,
                "hca_permit_type": self.reference_value(
                    "hca_permit", "hca_permit_type", "Investigation"
                ),
            },
        )
        hca_permit.save(**self.save_kwargs)

        requirements = [
            self.make_process_requirement(spec) for spec in self._REQUIREMENTS
        ]

        permit = self.new_resource("permit_application")
        self.append_blank_tile_for_group(
            permit,
            "application_identification",
            {
                "project_name": self.localized("My Project"),
                "application_id": self.localized("APP-1"),
            },
        )
        self.append_blank_tile_for_group(
            permit,
            "related_permit",
            {"related_permit": hca_permit, "is_related_permit": True},
        )
        permit.append_tile("application_admin")
        admin = permit.aliased_data.application_admin
        for i, (spec, requirement) in enumerate(zip(self._REQUIREMENTS, requirements)):
            if i > 0:
                admin.append_tile("process_requirement")
            child = admin.aliased_data.process_requirement[i]
            child.aliased_data.process_requirement_order = spec[
                "process_requirement_order"
            ]
            child.aliased_data.process_requirement = requirement
            child.aliased_data.ministry_assignee = assignees[i]
        permit.save(**self.save_kwargs)

        return DashboardDemoData(
            permit=permit,
            hca_permit=hca_permit,
            assignees=assignees,
            holders=holders,
            process_requirements=requirements,
        )
