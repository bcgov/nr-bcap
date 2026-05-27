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
    project_officer: ResourceTileTree
    unassigned_permit: ResourceTileTree | None = None


@dataclass
class PermitSpec:
    project_name: str
    application_id: str
    hca_permit: ResourceTileTree
    project_officer: ResourceTileTree
    children: list
    priority: str | None = None


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
    _PROJECT_OFFICER_NAME = ("Jordan", "Lee")
    _SEED_UNASSIGNED_PERMIT = True

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
        project_officer = self.make_contributor(
            contributor_type, *self._PROJECT_OFFICER_NAME
        )

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
        permit = self._make_permit(
            PermitSpec(
                project_name="My Project",
                application_id="APP-1",
                hca_permit=hca_permit,
                project_officer=project_officer,
                children=[
                    (requirement, spec["process_requirement_order"], assignee)
                    for spec, requirement, assignee in zip(
                        self._REQUIREMENTS, requirements, assignees
                    )
                ],
                priority="High",
            )
        )

        unassigned_permit = None
        if self._SEED_UNASSIGNED_PERMIT:
            # A second permit whose outstanding requirement has no
            # ministry_assignee, so the UNASSIGNED status filter has something
            # to surface.
            unassigned_requirement = self.make_process_requirement(
                {
                    "id": "REQ-2026-UNASSIGNED",
                    "name": "Awaiting assignment",
                    "due": "2026-05-01",
                    "notes": "check out this feature",
                    "satisfied": False,
                    "process_requirement_order": 1,
                    "sub_requirements": [],
                }
            )
            unassigned_permit = self._make_permit(
                PermitSpec(
                    project_name="Unassigned Project",
                    application_id="APP-2",
                    hca_permit=hca_permit,
                    project_officer=project_officer,
                    children=[(unassigned_requirement, 1, None)],
                    priority="Regular",
                )
            )

        return DashboardDemoData(
            permit=permit,
            unassigned_permit=unassigned_permit,
            hca_permit=hca_permit,
            assignees=assignees,
            holders=holders,
            process_requirements=requirements,
            project_officer=project_officer,
        )

    def _make_permit(self, spec: PermitSpec):
        """Create a permit_application from a PermitSpec: linked to its HCA
        Permit, with one application_admin child per requirement."""
        permit = self.new_resource("permit_application")
        self.append_blank_tile_for_group(
            permit,
            "application_identification",
            {
                "project_name": self.localized(spec.project_name),
                "application_id": self.localized(spec.application_id),
            },
        )
        self.append_blank_tile_for_group(
            permit,
            "related_permit",
            {"related_permit": spec.hca_permit, "is_related_permit": True},
        )
        permit.append_tile("application_admin")
        admin = permit.aliased_data.application_admin
        admin.aliased_data.project_officer = spec.project_officer
        if spec.priority is not None:
            admin.aliased_data.application_priority_level = self.reference_value(
                "permit_application", "application_priority_level", spec.priority
            )
        for i, (requirement, order, assignee) in enumerate(spec.children):
            if i > 0:
                admin.append_tile("process_requirement")
            child = admin.aliased_data.process_requirement[i]
            child.aliased_data.process_requirement_order = order
            child.aliased_data.process_requirement = requirement
            if assignee is not None:
                child.aliased_data.ministry_assignee = assignee
        permit.save(**self.save_kwargs)
        return permit
