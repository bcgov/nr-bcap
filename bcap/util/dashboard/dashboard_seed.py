"""Builds the dashboard demo graph -- a Permit Application linked to a Process
Requirement, an HCA Permit, and Contributors.

Shared by the dashboard service tests and the ``seed_dashboard_demo`` command,
and built through arches-querysets (via ``ResourceBuilder``) so it stays in sync
with how the service reads.
"""

from dataclasses import dataclass
from datetime import timezone as dt_timezone

from faker import Faker

from arches.app.models.models import EditLog
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
    requirement_templates: list[ResourceTileTree] | None = None


@dataclass
class HcaPermit:
    permit: ResourceTileTree
    holders: list[ResourceTileTree]


@dataclass
class SharedResources:
    """The resources that don't have to be recreated for every card. Built once
    by ``build_shared`` and passed to each ``build`` so a multi-card seed pays
    for them only on the first card. The pools (assignees, hca_permits) let each
    card draw a varied subset without recreating contributors/permits."""

    contributor_type: list
    assignees: list[ResourceTileTree]
    project_officers: list[ResourceTileTree]
    hca_permits: list[HcaPermit]
    requirement_templates: list[ResourceTileTree]


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

    # Appended to every generated name so seeded demo data is identifiable (and
    # easy to filter out) in the UI.
    _TEST_DATA_SUFFIX = "TEST-DATA-DASHBOARD"

    _HOLDER_COUNT = 2
    # Shared pools reused across cards: each card draws from them, so cards vary
    # without recreating these contributors/permits per card.
    _ASSIGNEE_POOL_SIZE = 6
    _HCA_POOL_SIZE = 4
    _OFFICER_POOL_SIZE = 4
    _SEED_UNASSIGNED_PERMIT = True
    _RANDOMIZE_NAME = True

    # Requirement names are composed prefix + suffix so they read sensibly while
    # giving many distinct combinations to randomize over.
    _REQUIREMENT_NAME_PREFIXES = [
        "Initial",
        "Preliminary",
        "Completeness",
        "Field",
        "Technical",
        "Archaeological",
        "Heritage",
        "Cultural",
        "Environmental",
        "Final",
        "Site",
    ]
    _REQUIREMENT_NAME_SUFFIXES = [
        "Review",
        "Assessment",
        "Inspection",
        "Consultation",
        "Check",
        "Evaluation",
        "Screening",
        "Sign-off",
        "Recommendation",
        "Survey",
    ]
    _PROJECT_TYPES = [
        "Pipeline",
        "Highway Expansion",
        "Subdivision",
        "Quarry",
        "Transmission Line",
        "Bridge Replacement",
        "Wind Farm",
        "Residential Development",
        "Site Survey",
    ]

    def __init__(self):
        super().__init__()
        self.faker = Faker()

    def _suffixed(self, name):
        return f"{name} {self._TEST_DATA_SUFFIX}"

    def _random_application_id(self):
        return self._suffixed(f"APP-{self.faker.random_int(min=1000, max=9999)}")

    def _random_due_date(self):
        """A due date spread around now, so some cards read as overdue and
        some as upcoming."""
        return self.faker.date_between(start_date="-30d", end_date="+180d").isoformat()

    def _random_permit_number(self):
        return self._suffixed(f"HCA-{self.faker.random_int(min=1000, max=9999)}")

    def _random_project_name(self):
        return self._suffixed(
            f"{self.faker.city()} {self.faker.random_element(self._PROJECT_TYPES)}"
        )

    def _randomize_assignee_change_date(self, permit):
        """ministry_assignee_change_date is derived from the edit-log timestamp
        of the assignment (there is no assignment-date node), so vary that
        timestamp to spread the seeded cards out."""
        changed = self.faker.date_time_between(
            start_date="-60d", end_date="now", tzinfo=dt_timezone.utc
        )
        EditLog.objects.filter(resourceinstanceid=str(permit.pk)).update(
            timestamp=changed
        )

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

    def _random_requirement_name(self):
        return self._suffixed(
            f"{self.faker.random_element(self._REQUIREMENT_NAME_PREFIXES)} "
            f"{self.faker.random_element(self._REQUIREMENT_NAME_SUFFIXES)}"
        )

    def _requirement_specs(self):
        """A fresh set of requirement specs, each with a randomized name. Called
        per card (and once for the templates) so requirement names vary."""
        names = []
        while len(names) < len(self._REQUIREMENTS):
            name = self._random_requirement_name()
            if name not in names:
                names.append(name)
        return [
            {
                **spec,
                "name": name if self._RANDOMIZE_NAME else spec["name"],
                "sub_requirements": [{**sub} for sub in spec["sub_requirements"]],
            }
            for spec, name in zip(self._REQUIREMENTS, names)
        ]

    def make_requirement_templates(self, specs):
        """Create one is_template_requirement=True requirement per spec. Once
        per run."""
        return [
            self.make_process_requirement({**spec, "is_template": True})
            for spec in specs
        ]

    def _make_working_requirement(self, spec):
        """A working-document requirement built fresh from a template's spec:
        is_template stays False and it gets its own due date. Built directly
        rather than cloned -- one queryset save instead of a deep copy plus a
        reload and second save."""
        return self.make_process_requirement(
            {**spec, "is_template": False, "due": self._random_due_date()}
        )

    def _make_hca_permit(self, contributor_type):
        """An HCA permit with its own holders and a random number/type."""
        holders = [
            self.make_contributor(
                contributor_type, None, self._suffixed(self.faker.company())
            )
            for _ in range(self._HOLDER_COUNT)
        ]
        hca_permit = self.new_resource("hca_permit")
        self.append_blank_tile_for_group(
            hca_permit,
            "permit_identification",
            {
                "permit_number": self._random_permit_number(),
                "permit_holder": holders,
                "hca_permit_type": self.random_reference_value(
                    "hca_permit", "hca_permit_type"
                ),
            },
        )
        hca_permit.save(**self.save_kwargs)
        return HcaPermit(permit=hca_permit, holders=holders)

    def build_shared(self):
        """Create the resources a card can reuse rather than recreate: the
        contributor and HCA-permit pools and the requirement template set. Call
        once per run and pass the result to ``build`` -- these dominate the
        per-card cost, so sharing them across cards is most of the speedup."""
        contributor_type = self.reference_value("contributor", "contributor_type")

        # Pools each card draws from, so cards vary without recreating these.
        assignees = [
            self.make_contributor(
                contributor_type,
                self.faker.first_name(),
                self._suffixed(self.faker.last_name()),
            )
            for _ in range(self._ASSIGNEE_POOL_SIZE)
        ]
        hca_permits = [
            self._make_hca_permit(contributor_type) for _ in range(self._HCA_POOL_SIZE)
        ]
        project_officers = [
            self.make_contributor(
                contributor_type,
                self.faker.first_name(),
                self._suffixed(self.faker.last_name()),
            )
            for _ in range(self._OFFICER_POOL_SIZE)
        ]

        return SharedResources(
            contributor_type=contributor_type,
            assignees=assignees,
            project_officers=project_officers,
            hca_permits=hca_permits,
            requirement_templates=self.make_requirement_templates(
                self._requirement_specs()
            ),
        )

    def build(self, shared=None):
        """Create one card's resources and return everything the run produced.
        The seed command builds ``shared`` once and passes it to every card so
        the contributors/HCA permit/templates are paid for once; tests omit it
        and get a per-build set."""
        if shared is None:
            shared = self.build_shared()

        # Fresh specs (with randomized names) per card, so requirements vary.
        card_specs = self._requirement_specs()
        # Each requirement on the permit is a working document built from one
        # spec (one per spec/assignee, ordered).
        requirements = [self._make_working_requirement(spec) for spec in card_specs]
        # Draw this card's assignees and HCA permit from the shared pools, so
        # cards differ without creating new contributors/permits.
        card_assignees = list(
            self.faker.random_elements(
                elements=shared.assignees, length=len(requirements), unique=True
            )
        )
        hca = self.faker.random_element(shared.hca_permits)
        project_officer = self.faker.random_element(shared.project_officers)
        permit = self._make_permit(
            PermitSpec(
                project_name=self._random_project_name(),
                application_id=self._random_application_id(),
                hca_permit=hca.permit,
                project_officer=project_officer,
                children=[
                    (requirement, order, assignee)
                    for order, (requirement, assignee) in enumerate(
                        zip(requirements, card_assignees), start=1
                    )
                ],
                priority="High",
            )
        )

        unassigned_permit = None
        if self._SEED_UNASSIGNED_PERMIT:
            # A second permit whose outstanding requirement has no
            # ministry_assignee, so the UNASSIGNED status filter has something
            # to surface. Use an unsatisfied spec -- a satisfied one would leave
            # the permit with no active requirement and no card at all.
            outstanding = next(spec for spec in card_specs if not spec["satisfied"])
            unassigned_requirement = self._make_working_requirement(outstanding)
            unassigned_permit = self._make_permit(
                PermitSpec(
                    project_name=self._random_project_name(),
                    application_id=self._random_application_id(),
                    hca_permit=hca.permit,
                    project_officer=project_officer,
                    children=[(unassigned_requirement, 1, None)],
                    priority="Regular",
                )
            )

        return DashboardDemoData(
            permit=permit,
            unassigned_permit=unassigned_permit,
            hca_permit=hca.permit,
            assignees=card_assignees,
            holders=hca.holders,
            process_requirements=requirements,
            project_officer=project_officer,
            requirement_templates=shared.requirement_templates,
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
        proposed = self.append_blank_tile_for_group(permit, "proposed_project", {})
        proposed.aliased_data.development_project_details.aliased_data.industrial_sector = self.random_reference_value(
            "permit_application", "industrial_sector"
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
        self._randomize_assignee_change_date(permit)
        return permit
