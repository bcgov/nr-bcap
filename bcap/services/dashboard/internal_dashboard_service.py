from dataclasses import replace
from itertools import chain

from django.db.models import (
    Exists,
    F,
    IntegerField,
    Max,
    OuterRef,
    Subquery,
    TextField,
    UUIDField,
    Value,
)
from django.db.models.fields.json import KeyTextTransform, KeyTransform
from django.db.models.functions import Cast, Coalesce

from arches.app.models.models import EditLog, TileModel

from arches_querysets.models import ResourceTileTree

from bcap.services.dashboard.base_dashboard_service import BaseDashboardService
from bcap.services.dashboard.dashboard_types import (
    InternalDashboardData,
    DashboardFilter,
    InternalDashboardCard,
    InternalDashboardPage,
    InternalDashboardStatus,
    Requirement,
)
from bcap.util.aliases.permit_application import PermitApplicationAliases
from bcap.util.aliases.process_requirement import ProcessRequirementAliases
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.queryset import filter_or_empty


class InternalDashboardService(BaseDashboardService):
    PR = ProcessRequirementAliases

    def get_cards(
        self, query: DashboardFilter, username: str = ""
    ) -> InternalDashboardPage:
        """Build dashboard cards from Permit Application resources and their
        related Process Requirement, HCA Permit, and Contributor resources.

        Per-field mappings are documented as help_text on the card dataclass."""
        count, permits = self._permits(query, username)
        requirements_by_permit = self._requirement_tiles_by_permit(permits)
        hca_permits = self._hca_permits(permits)
        # One traversal of the requirement tiles yields both the requirement ids
        # and the assignee ids the cards need.
        tiles = chain.from_iterable(requirements_by_permit.values())
        referenced = self._referenced_ids_by_alias(
            tiles, [self.PA.PROCESS_REQUIREMENT, self.PA.MINISTRY_ASSIGNEE]
        )
        chosen_by_permit = self._choose_requirements(
            requirements_by_permit, referenced[self.PA.PROCESS_REQUIREMENT]
        )
        officer_ids = self._referenced_ids(permits, self.PA.PROJECT_OFFICER)
        data = InternalDashboardData(
            chosen_by_permit=chosen_by_permit,
            assignee_dates=self._assignee_change_dates(chosen_by_permit),
            hca_permits=hca_permits,
            contributor_names=self._contributor_names(
                referenced[self.PA.MINISTRY_ASSIGNEE] | officer_ids, hca_permits
            ),
        )
        return InternalDashboardPage(
            count=count,
            page=query.page,
            limit=query.limit,
            results=self._cards_to_json(permits, data),
        )

    def _base_permit_queryset(self):
        """Permit applications with the card's nodes loaded (including the
        process_requirement tiles, so _requirement_tiles_by_permit needs no extra
        query) and the active assignee annotated, narrowed to those with an
        unsatisfied requirement."""
        queryset = (
            ResourceTileTree.get_tiles(
                GraphSlugs.PERMIT_APPLICATION,
                nodes=self._nodes(
                    GraphSlugs.PERMIT_APPLICATION,
                    [
                        self.PA.PROJECT_NAME,
                        self.PA.APPLICATION_ID,
                        self.PA.INDUSTRIAL_SECTOR,
                        self.PA.APPLICATION_PRIORITY_LEVEL,
                        self.PA.RELATED_PERMIT,
                        self.PA.PROCESS_REQUIREMENT,
                        self.PA.PROCESS_REQUIREMENT_ORDER,
                        self.PA.MINISTRY_ASSIGNEE,
                        self.PA.PROJECT_OFFICER,
                    ],
                ),
                as_representation=True,
            )
            .select_related("graph")
            .order_by("pk")  # stable, so LIMIT/OFFSET pages don't overlap
        )
        queryset = queryset.annotate(
            active_assignee=self._active_assignee_subquery(),
        )
        # No actionable requirement -> no card. Exists() stops at the first
        # matching tile.
        return queryset.filter(Exists(self._active_requirement_tiles()))

    def _permits(self, query, username=""):
        """The query's page of permits and the total count; counting, paging,
        and the status filter all run in the DB."""
        queryset = self._filter_by_status(
            self._base_permit_queryset(), query.status, username
        )
        return self._page(queryset, query)

    def _filter_by_status(self, queryset, status, username):
        """Narrow permits by the active requirement's ministry_assignee."""
        match status:
            case InternalDashboardStatus.UNASSIGNED:
                return queryset.filter(active_assignee__isnull=True)
            case InternalDashboardStatus.ASSIGNED_TO_ME:
                if not username:
                    raise ValueError(f"username is required for status {status}")
                my_contributor_id = self.contributors.username_contributor_id(username)
                # Avoid returning unassigned.
                return filter_or_empty(queryset, active_assignee=my_contributor_id)
            case _:
                return queryset

    def _active_assignee_subquery(self):
        """Per permit, the ministry_assignee id of its active requirement."""
        return Subquery(self._active_requirement_tiles().values("assignee")[:1])

    def _active_requirement_tiles(self):
        """Per-permit subquery of its unsatisfied process_requirement tiles that
        reference a real requirement, lowest order first. The non-null guard
        keeps this in lockstep with _choose_requirements, so a blank tile never
        makes a permit appear with no card."""
        app, req = GraphSlugs.PERMIT_APPLICATION, GraphSlugs.PROCESS_REQUIREMENT
        order_id, child_ng = self._node_info(app, self.PA.PROCESS_REQUIREMENT_ORDER)
        assignee_id = self._node_id(app, self.PA.MINISTRY_ASSIGNEE)
        requirement_id = self._node_id(app, self.PA.PROCESS_REQUIREMENT)
        status_id, status_ng = self._node_info(req, self.PR.REQUIREMENT_STATUS)

        def get_json_resource_id(node_id):
            return KeyTextTransform(
                "resourceId", KeyTransform("0", KeyTransform(node_id, "data"))
            )

        satisfied_ids = TileModel.objects.filter(
            nodegroup_id=status_ng, **{f"data__{status_id}": True}
        ).values_list("resourceinstance_id", flat=True)
        return (
            TileModel.objects.filter(
                resourceinstance_id=OuterRef("pk"), nodegroup_id=child_ng
            )
            .annotate(
                requirement=Cast(get_json_resource_id(requirement_id), UUIDField()),
                assignee=get_json_resource_id(assignee_id),
                order_value=Cast(KeyTextTransform(order_id, "data"), IntegerField()),
            )
            .exclude(requirement__in=satisfied_ids)
            .filter(requirement__isnull=False)
            .order_by("order_value")
        )

    def _requirement_tiles_by_permit(self, permits):
        """Map permit id -> its process_requirement tiles, sorted by order. Read
        from the already-loaded tree (see _base_permit_queryset), so no query."""
        requirements_by_permit = {}
        for permit in permits:
            tiles = []
            for admin in self._nested_tiles(permit.aliased_data.application_admin):
                tiles += self._nested_tiles(admin.aliased_data.process_requirement)
            requirements_by_permit[str(permit.pk)] = sorted(
                tiles, key=self._requirement_order
            )
        return requirements_by_permit

    def _contributor_names(self, assignee_ids, hca_permits):
        """Map id -> display name for every Contributor a card references: each
        tile's ministry_assignee plus each HCA Permit's permit_holder(s)."""
        ids = set(assignee_ids)
        for hca in hca_permits.values():
            ids.update(hca.holder_ids)
        return self.contributors.names_by_contributor_id(ids)

    def _choose_requirements(self, requirements_by_permit, requirement_ids):
        """Map permit id -> Requirement: per permit, the unsatisfied requirement
        whose tile has the lowest process_requirement_order (the row the card
        surfaces), or None when every requirement is satisfied. requirement_ids
        are the referenced requirements to resolve statuses for."""
        # Resolve the referenced requirements first, dropping satisfied ones so
        # membership in `requirements` is the "is unsatisfied?" test below.
        requirements = {}
        if requirement_ids:
            resources = self._resources(
                GraphSlugs.PROCESS_REQUIREMENT,
                requirement_ids,
                [
                    self.PR.REQUIREMENT_STATUS,
                    self.PR.REQUIREMENT_NAME,
                    self.PR.REQUIREMENT_PROCESS_DUE_DATE,
                    self.PR.ASSESSMENT_NOTES,
                ],
            )
            for requirement in resources:
                data = requirement.aliased_data
                identification = data.requirement_identification.aliased_data
                duration = data.requirement_execution_duration.aliased_data
                assessment = data.sub_requirement_assessment_n1.aliased_data
                if assessment.requirement_status["node_value"]:
                    continue
                requirements[str(requirement.pk)] = Requirement(
                    name=identification.requirement_name["display_value"],
                    due_date=duration.requirement_process_due_date["display_value"],
                    # The card drills in to the unsatisfied requirement itself.
                    route=str(requirement.pk),
                    notes=assessment.assessment_notes["display_value"],
                )

        chosen = {}
        for permit_id, tiles in requirements_by_permit.items():
            # Tiles are sorted by order upstream, so the first unsatisfied wins.
            # Attach the chosen tile to a copy so the shared lookup keeps tile=None.
            chosen[permit_id] = None
            for tile in tiles:
                requirement_id = self._resource_id(
                    tile.aliased_data.process_requirement
                )
                requirement = requirements.get(requirement_id)
                if requirement:
                    chosen[permit_id] = replace(requirement, tile=tile)
                    break
        return chosen

    def _requirement_order(self, tile):
        """A tile's process_requirement_order as a sort key; tiles with no order
        value sort last (infinity) so a tile that has one always wins."""
        value = tile.aliased_data.process_requirement_order
        return value["node_value"] if value else float("inf")

    def _assignee_change_dates(self, chosen_by_permit):
        """Map requirement-tile id -> date its ministry_assignee last changed.
        There's no assignment-date node, so we read it from the edit log: the
        latest timestamp where the assignee node's value actually changed."""
        tiles = [c.tile for c in chosen_by_permit.values() if c is not None]
        tile_ids = [str(tile.pk) for tile in tiles]
        if not tile_ids:
            return {}

        node_id = self._node_id(
            GraphSlugs.PERMIT_APPLICATION, self.PA.MINISTRY_ASSIGNEE
        )

        # NULL-coalesced so an initial assignment (key absent in oldvalue)
        # registers as a change rather than NULL == NULL.
        def assignee(column):
            return Coalesce(
                KeyTextTransform(node_id, column),
                Value(""),
                output_field=TextField(),
            )

        rows = (
            EditLog.objects.filter(tileinstanceid__in=tile_ids)
            .annotate(
                new_assignee=assignee("newvalue"),
                old_assignee=assignee("oldvalue"),
            )
            .exclude(new_assignee=F("old_assignee"))
            .values("tileinstanceid")
            .annotate(changed=Max("timestamp"))
        )
        return {str(row["tileinstanceid"]): row["changed"].isoformat() for row in rows}

    def _cards_to_json(self, permits, data: InternalDashboardData):
        """A card for each permit, assembled from the gathered lookups."""
        cards = []
        for permit in permits:
            cards.append(self._card_to_json(permit, data))
        return cards

    def _card_to_json(self, permit, data: InternalDashboardData):
        """Assemble one permit's card from its tiles and the gathered lookups.
        The full field mapping is documented on get_cards."""
        PA = PermitApplicationAliases
        aliased = permit.aliased_data
        requirement = data.chosen_by_permit[str(permit.pk)]
        tile = requirement.tile
        core = self._application_core(aliased)

        hca = self._related_hca(core.related_permit_id, data.hca_permits)
        holder_names = self._join_names(hca.holder_ids, data.contributor_names)

        assignee_id = self._resource_id(tile.aliased_data.ministry_assignee)
        ministry_assignee_name = data.contributor_names.get(assignee_id, "")
        ministry_assignee_change_date = data.assignee_dates.get(str(tile.pk), "")

        officer_id = self._resource_id(self._node_value(aliased, PA.PROJECT_OFFICER))
        officer_name = data.contributor_names.get(officer_id, "")

        return InternalDashboardCard(
            id=str(permit.pk),
            requirement_name=requirement.name,
            requirement_due_date=requirement.due_date,
            project_name=core.project_name,
            application_number=core.application_number,
            industrial_sector=core.industrial_sector,
            permit_id=core.related_permit_id,
            permit_number=hca.number,
            permit_holder=holder_names,
            permit_holder_ids=hca.holder_ids,
            project_officer=officer_name,
            project_officer_id=officer_id,
            assessment_notes=requirement.notes,
            ministry_assignee_name=ministry_assignee_name,
            ministry_assignee_id=assignee_id,
            ministry_assignee_change_date=ministry_assignee_change_date,
            requirement_id=requirement.route,
            urgency=0,
            priority_level=core.priority_level,
        )
