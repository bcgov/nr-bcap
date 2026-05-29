"""Business operations on a Process Requirement resource (arches-querysets tile
tree). HTTP-agnostic: callers load, mutate, and save the resource themselves."""

from datetime import date
from enum import StrEnum

from arches_querysets.models import ResourceTileTree, TileTree
from arches_querysets.querysets import ResourceTileTreeQuerySet

from bcap.services.exceptions import StaleReference
from bcap.services.process_requirement.process_requirement_types import (
    ProcessRequirement,
    SubRequirement,
)
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.dates import to_iso
from bcap.util.localized_string import to_text
from bcap.util.sentinels import UNCHANGED, _Unchanged

# A date to set, None to clear, or UNCHANGED to leave as-is (partial update).
DateInput = date | None | _Unchanged


class Group(StrEnum):
    """Grouping (semantic) node aliases -- regen_aliases skips semantic nodes."""

    DATES = "requirement_execution_duration"
    SUB_REQUIREMENT = "sub_requirement"


class ProcessRequirementService:
    """Edits an existing Process Requirement; it never creates one."""

    GRAPH = GraphSlugs.PROCESS_REQUIREMENT

    def get_queryset(self) -> ResourceTileTreeQuerySet:
        """Tile-tree queryset of Process Requirements."""
        return ResourceTileTree.get_tiles(self.GRAPH)

    def set_requirement_process_dates(
        self,
        resource: ResourceTileTree,
        start_date: DateInput,
        due_date: DateInput,
        completion_date: DateInput,
    ) -> None:
        """Apply each date; UNCHANGED skips it, None clears it."""
        if (
            start_date is UNCHANGED
            and due_date is UNCHANGED
            and completion_date is UNCHANGED
        ):
            return
        duration = resource.aliased_data.requirement_execution_duration
        if duration is None:
            resource.append_tile(Group.DATES)
            duration = resource.aliased_data.requirement_execution_duration
        dates = duration.aliased_data
        if start_date is not UNCHANGED:
            dates.requirement_process_start_date = to_iso(start_date)
        if due_date is not UNCHANGED:
            dates.requirement_process_due_date = to_iso(due_date)
        if completion_date is not UNCHANGED:
            dates.requirement_process_completion_date = to_iso(completion_date)

    def edit_sub_requirements(
        self, resource: ResourceTileTree, subs: list[SubRequirement] | None
    ) -> None:
        """Edit subs by id or add id-less ones; omitted fields and a None list
        are no-ops."""
        if subs is None:
            return
        existing = {str(t.pk): t for t in resource.aliased_data.sub_requirement}
        for sub in subs:
            tile = self.resolve_sub_requirement_tile(resource, existing, sub)
            data = tile.aliased_data
            if sub.name is not None:
                data.sub_requirement_name = sub.name
            if sub.satisfied is not None:
                data.sub_requirement_satisfied = sub.satisfied
            if sub.assessment_notes is not None:
                data.sub_requirement_assessment_notes = sub.assessment_notes
            if sub.sort_order is not None:
                data.sub_requirement_sort_order = sub.sort_order

    def resolve_sub_requirement_tile(
        self,
        resource: ResourceTileTree,
        existing: dict[str, TileTree],
        sub: SubRequirement,
    ) -> TileTree:
        """The tile for `sub`, matched by id or appended new. Unknown id raises
        (not a silent re-create); a new sub needs a name and sort_order."""
        if sub.id:
            tile = existing.get(sub.id)
            if tile is None:
                raise StaleReference(
                    f"Sub-requirement {sub.id} not found on this requirement."
                )
            return tile
        if not sub.name:
            raise ValueError("A new sub-requirement needs a name.")
        if sub.sort_order is None:
            raise ValueError("A new sub-requirement needs a sort order.")
        resource.append_tile(Group.SUB_REQUIREMENT)
        return resource.aliased_data.sub_requirement[-1]

    def to_output(self, resource: ResourceTileTree) -> ProcessRequirement:
        """The managed fields of the (saved) requirement."""
        duration = resource.aliased_data.requirement_execution_duration
        dates = duration.aliased_data if duration else None

        sub_requirements = []
        for tile in resource.aliased_data.sub_requirement:
            data = tile.aliased_data
            sub_requirements.append(
                SubRequirement(
                    id=str(tile.pk),
                    name=to_text(data.sub_requirement_name),
                    satisfied=data.sub_requirement_satisfied,
                    assessment_notes=to_text(data.sub_requirement_assessment_notes),
                    sort_order=data.sub_requirement_sort_order,
                )
            )
        sub_requirements.sort(key=lambda s: (s.sort_order is None, s.sort_order))

        return ProcessRequirement(
            id=str(resource.pk),
            start_date=dates and dates.requirement_process_start_date,
            due_date=dates and dates.requirement_process_due_date,
            completion_date=dates and dates.requirement_process_completion_date,
            sub_requirements=sub_requirements,
        )
