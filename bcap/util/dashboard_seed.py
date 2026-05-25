"""Builds the dashboard demo graph -- a Permit Application linked to a Process
Requirement, an HCA Permit, and Contributors.

Shared by the dashboard service tests and the ``seed_dashboard_demo`` command,
and built through arches-querysets so it stays in sync with how the service
reads.
"""

from dataclasses import dataclass

from django.utils import timezone

from arches.app.models.models import (
    GraphModel,
    Node,
    ResourceInstance,
    ResourceInstanceLifecycleState,
)

from arches_controlled_lists.models import ListItem
from arches_querysets.models import AliasedData, ResourceTileTree


@dataclass
class DashboardDemoData:
    permit: ResourceTileTree
    hca_permit: ResourceTileTree
    assignees: list[ResourceTileTree]
    holders: list[ResourceTileTree]
    process_requirements: list[ResourceTileTree]
    sub_requirement_tile_ids: list[str | None]


class DashboardDemoBuilder:
    """Create the demo graph and return the resources it produced.

    Builds a Permit Application with all three process requirements (the first
    fully satisfied, the rest still outstanding
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
            "sub_satisfied": [True, True, True],
            "order": 1,
        },
        {
            "id": "REQ-2026-002",
            "name": "Field Assessment",
            "due": "2026-02-15",
            "notes": "awaiting site access",
            "satisfied": False,
            "sub_satisfied": [False, True, False],
            "order": 2,
        },
        {
            "id": "REQ-2026-003",
            "name": "Final Sign-off",
            "due": "2026-03-30",
            "notes": "pending manager approval",
            "satisfied": False,
            "sub_satisfied": [False, False, True],
            "order": 3,
        },
    ]

    _SUB_REQUIREMENTS = [
        {"name": "Submit application forms", "sort_order": 1},
        {"name": "Schedule site inspection", "sort_order": 2},
        {"name": "Final review", "sort_order": 3},
    ]

    @staticmethod
    def localized(value):
        """A `string` datatype value."""
        return {"en": {"value": value, "direction": "ltr"}}

    @staticmethod
    def reference_value(slug, alias, label=None):
        """A `reference` value from a node's controlled list: the item matching
        ``label``, or the first item if ``label`` is None."""
        node = Node.objects.get(graph__slug=slug, alias=alias, source_identifier=None)
        list_id = node.config.get("controlledList")
        items = ListItem.objects.filter(list_id=list_id)
        if label is not None:
            item = items.filter(list_item_values__value=label).first()
        else:
            item = items.order_by("sortorder").first()
        if item is None:
            raise RuntimeError(
                f"Controlled list {list_id} backing {slug}.{alias} has no "
                f"{'matching ' if label else ''}items; load its reference data first."
            )
        return [str(item.pk)]

    @staticmethod
    def _append_group(container, grouping_alias, values):
        """Append a blank tile for ``grouping_alias`` and set its node values by alias."""
        container.append_tile(grouping_alias)
        tile = getattr(container.aliased_data, grouping_alias)
        if isinstance(tile, list):
            tile = tile[-1]
        for alias, value in values.items():
            setattr(tile.aliased_data, alias, value)
        return tile

    def _graph_id(self, slug):
        """Cache slug -> graphid; _new_resource is called once per resource but
        there are only a handful of distinct graphs."""
        if slug not in self._graph_ids:
            self._graph_ids[slug] = GraphModel.objects.get(slug=slug).pk
        return self._graph_ids[slug]

    def _new_resource(self, slug):
        """A fresh ResourceTileTree with its resource row already persisted."""
        resource = ResourceTileTree(
            graph_id=self._graph_id(slug),
            resource_instance_lifecycle_state=self.state,
            createdtime=timezone.now(),
        )
        resource.aliased_data = AliasedData()
        ResourceInstance.objects.create(
            pk=resource.pk,
            graph_id=resource.graph_id,
            resource_instance_lifecycle_state=self.state,
            createdtime=timezone.now(),
        )
        return resource

    def _make_contributor(self, contributor_type, first_name, name):
        """``first_name`` is None for an organization."""
        contributor = self._new_resource("contributor")
        self._append_group(
            contributor,
            "contributor",
            {
                "first_name": self.localized(first_name) if first_name else None,
                "contributor_name": self.localized(name),
                "contributor_type": contributor_type,
            },
        )
        contributor.save(**self.save_kwargs)
        return contributor

    def _make_process_requirement(self, spec):
        """Returns the requirement and the tile id of the sub-requirement the
        dashboard routes to, or None when the requirement is fully satisfied."""
        requirement = self._new_resource("process_requirement")
        # requirement_identification is a grouping node that also holds a required value.
        self._append_group(
            requirement,
            "requirement_identification",
            {
                "requirement_identification": self.localized(spec["id"]),
                "requirement_name": self.localized(spec["name"]),
            },
        )
        self._append_group(
            requirement,
            "requirement_execution_duration",
            {"requirement_process_due_date": spec["due"]},
        )
        self._append_group(
            requirement,
            "sub_requirement_assessment_n1",
            {
                "requirement_status": spec["satisfied"],
                "assessment_notes": self.localized(spec["notes"]),
            },
        )
        sub_done = spec["sub_satisfied"]
        sub_tiles = [
            self._append_group(
                requirement,
                "sub_requirement",
                {
                    "sub_requirement_name": self.localized(sub["name"]),
                    "sub_requirement_satisfied": done,
                    "sub_requirement_sort_order": sub["sort_order"],
                },
            )
            for sub, done in zip(self._SUB_REQUIREMENTS, sub_done)
        ]
        requirement.save(**self.save_kwargs)
        route_tile = next(
            (tile for tile, done in zip(sub_tiles, sub_done) if not done), None
        )
        return requirement, str(route_tile.pk) if route_tile is not None else None

    def build(self):
        """Create the demo graph and return the resources it produced."""
        self.state = ResourceInstanceLifecycleState.objects.first()
        self.save_kwargs = {"force_admin": True, "partial": False, "index": False}
        self._graph_ids = {}
        contributor_type = self.reference_value("contributor", "contributor_type")

        assignees = [
            self._make_contributor(contributor_type, first, last)
            for first, last in self._ASSIGNEE_NAMES
        ]
        holders = [
            self._make_contributor(contributor_type, None, org)
            for org in self._HOLDER_NAMES
        ]

        hca_permit = self._new_resource("hca_permit")
        self._append_group(
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

        requirements, route_ids = [], []
        for spec in self._REQUIREMENTS:
            requirement, route_id = self._make_process_requirement(spec)
            requirements.append(requirement)
            route_ids.append(route_id)

        permit = self._new_resource("permit_application")
        self._append_group(
            permit,
            "application_identification",
            {
                "project_name": self.localized("My Project"),
                "application_id": self.localized("APP-1"),
            },
        )
        self._append_group(
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
            child.sortorder = spec["order"]
            child.aliased_data.process_requirement = requirement
            child.aliased_data.ministry_assignee = assignees[i]
        permit.save(**self.save_kwargs)

        return DashboardDemoData(
            permit=permit,
            hca_permit=hca_permit,
            assignees=assignees,
            holders=holders,
            process_requirements=requirements,
            sub_requirement_tile_ids=route_ids,
        )
