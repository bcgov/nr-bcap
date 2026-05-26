from dataclasses import dataclass, field, replace
from itertools import chain

from django.db.models import (
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

from arches.app.models.models import EditLog, Node, TileModel

from arches_querysets.models import ResourceTileTree, TileTree

from bcap.services.dashboard.dashboard_types import (
    DashboardCard,
    DashboardPage,
    DashboardFilter,
)
from bcap.services.dashboard.base_graph_service import BaseGraphService
from bcap.util.aliases.contributor import ContributorAliases
from bcap.util.aliases.hca_permit import HCAPermitAliases
from bcap.util.aliases.permit_application import PermitApplicationAliases
from bcap.util.aliases.process_requirement import ProcessRequirementAliases
from bcap.util.bcap_aliases import GraphSlugs


@dataclass
class HcaPermit:
    """An HCA Permit related to a permit application."""

    number: str = ""
    holder_ids: list[str] = field(default_factory=list)


@dataclass
class Requirement:
    """An unsatisfied process requirement as the card needs it, paired with the
    permit's process_requirement tile that points at it. The tile carries the
    ministry_assignee and the id the assignee edit-log date is keyed by; it stays
    None on the empty Requirement used when a permit has none unsatisfied."""

    name: str = ""
    due_date: str = ""
    route: str = ""
    notes: str = ""
    tile: TileTree | None = None


@dataclass
class DashboardData:
    """The per-permit lookups a card is assembled from, keyed by permit/tile id."""

    chosen_by_permit: dict[str, Requirement | None]
    assignee_dates: dict[str, str]
    hca_permits: dict[str, HcaPermit]
    contributor_names: dict[str, str]


class DashboardService(BaseGraphService):
    PA = PermitApplicationAliases
    PR = ProcessRequirementAliases
    # Shown in the CAP row when a permit has no unsatisfied requirement.
    ALL_SATISFIED_LABEL = "All requirements met"
    # status filter value: permits whose active requirement has no assignee.
    STATUS_UNASSIGNED = "UNASSIGNED"

    def get_cards(self, query: DashboardFilter) -> DashboardPage:
        """Build dashboard cards from Permit Application resources and their
        related Process Requirement, HCA Permit, and Contributor resources.

        Field mapping (see the dashboard card dataclass):
          id             <- permit_application resourceinstanceid (drill-in GUID)
          body_title     <- permit_application.project_name
          body_subtitle1 <- permit_application.application_id
          body_subtitle2 <- permit_application.industrial_sector (reference label)
          cap_label      <- chosen requirement's requirement_name, or
                            ALL_SATISFIED_LABEL when none are unsatisfied
          cap_date       <- chosen requirement's requirement_process_due_date
          body1          <- related HCA Permit.permit_number
          body2          <- related HCA Permit.permit_holder (Contributor name)
          body3          <- Project Officer (not working locally for me)
          body4          <- chosen requirement's assessment_notes
          footer_name    <- chosen tile's ministry_assignee (Contributor) name
          footer_date    <- edit-log timestamp of the last change to that tile's
                            ministry_assignee node (assignee_change_dates)
          route          <- chosen (first unsatisfied) Process Requirement
                            resourceinstanceid; falls back to the permit's own
                            id when none are unsatisfied (drill-in target)
          cap_priority   <- permit_application.application_priority_level
                            (reference label)

        not yet specified, placeholders: body5, urgency.
        """
        if query.order_by:
            raise NotImplementedError("order_by is not supported yet")
        count, permits = self._permits(query)
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
        data = DashboardData(
            chosen_by_permit=chosen_by_permit,
            assignee_dates=self._assignee_change_dates(chosen_by_permit),
            hca_permits=hca_permits,
            contributor_names=self._contributor_names(
                referenced[self.PA.MINISTRY_ASSIGNEE], hca_permits
            ),
        )
        return DashboardPage(
            count=count,
            page=query.page,
            limit=query.limit,
            results=self._cards_to_json(permits, data),
        )

    def _permits(self, query):
        """The query's page of permits and the total count, counting, paging,
        and the contributor/status filters all run in the DB. Loads the
        process_requirement tiles in the same pass (they nest under
        application_admin), so _requirement_tiles_by_permit needs no extra
        query."""
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
                    ],
                ),
                as_representation=True,
            )
            .select_related("graph")
            .order_by("pk")  # stable, so LIMIT/OFFSET pages don't overlap
        )
        if query.contributor_id or query.status == self.STATUS_UNASSIGNED:
            queryset = queryset.annotate(
                active_requirement=self._active_requirement_subquery(),
                active_assignee=self._active_assignee_subquery(),
            )
        if query.contributor_id:
            queryset = queryset.filter(active_assignee=str(query.contributor_id))
        if query.status == self.STATUS_UNASSIGNED:
            queryset = queryset.filter(
                active_requirement__isnull=False, active_assignee__isnull=True
            )

        start = (query.page - 1) * query.limit
        return queryset.count(), list(queryset[start : start + query.limit])

    def _active_assignee_subquery(self):
        """Per permit, the ministry_assignee id of its active requirement."""
        return Subquery(self._active_requirement_tiles().values("assignee")[:1])

    def _active_requirement_subquery(self):
        """Per permit, the resource id of its active requirement (null if none)."""
        return Subquery(self._active_requirement_tiles().values("requirement")[:1])

    def _active_requirement_tiles(self):
        """Per-permit subquery (via OuterRef) of its unsatisfied
        process_requirement tiles, lowest order first; the first row is the
        active one the card surfaces."""
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
            .order_by("order_value")
        )

    def _requirement_tiles_by_permit(self, permits):
        """Map permit id -> its process_requirement tiles, sorted by
        process_requirement_order so the first is the one the card surfaces (the
        query has no inherent order). The tiles were loaded with the permits (see
        _permits), so this just reads them out of the loaded tree -- no query. A
        permit has many such tiles (one per requirement/assignee pair)."""
        requirements_by_permit = {}
        for permit in permits:
            tiles = []
            for admin in self._nested_tiles(permit.aliased_data.application_admin):
                tiles += self._nested_tiles(admin.aliased_data.process_requirement)
            requirements_by_permit[str(permit.pk)] = sorted(
                tiles, key=self._requirement_order
            )
        return requirements_by_permit

    def _hca_permits(self, permits):
        """Map id -> HcaPermit for the permits' related_permit links."""
        ids = self._referenced_ids(permits, self.PA.RELATED_PERMIT)
        if not ids:
            return {}

        resources = self._resources(
            GraphSlugs.HCA_PERMIT,
            ids,
            [HCAPermitAliases.PERMIT_NUMBER, HCAPermitAliases.PERMIT_HOLDER],
        )

        hca_permits = {}
        for permit in resources:
            # permit_identification is a cardinality-1 top-level group.
            identification = permit.aliased_data.permit_identification.aliased_data
            hca_permits[str(permit.pk)] = HcaPermit(
                number=identification.permit_number["display_value"],
                holder_ids=self._resource_ids(identification.permit_holder),
            )
        return hca_permits

    def _contributor_names(self, assignee_ids, hca_permits):
        """Map id -> display name for every Contributor involved: each tile's
        ministry_assignee plus each HCA Permit's permit_holder(s)."""
        ids = set(assignee_ids)
        for hca in hca_permits.values():
            ids.update(hca.holder_ids)
        if not ids:
            return {}

        resources = self._resources(
            GraphSlugs.CONTRIBUTOR,
            ids,
            [ContributorAliases.FIRST_NAME, ContributorAliases.CONTRIBUTOR_NAME],
        )

        names = {}
        for contributor in resources:
            data = contributor.aliased_data.contributor.aliased_data
            first = data.first_name["display_value"]
            last = data.contributor_name["display_value"]
            names[str(contributor.pk)] = " ".join(filter(None, (first, last)))
        return names

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
            chosen[permit_id] = next(
                (
                    replace(requirement, tile=tile)
                    for tile in tiles
                    if (
                        requirement := requirements.get(
                            self._resource_id(tile.aliased_data.process_requirement)
                        )
                    )
                ),
                None,
            )
        return chosen

    def _requirement_order(self, tile):
        """A tile's process_requirement_order as a sort key; tiles with no order
        value sort last (infinity) so a tile that has one always wins."""
        value = getattr(tile.aliased_data, self.PA.PROCESS_REQUIREMENT_ORDER)
        return value["node_value"] if value else float("inf")

    def _assignee_change_dates(self, chosen_by_permit):
        """Map requirement-tile id -> date its ministry_assignee last changed.
        There's no assignment-date node, so we read it from the edit log: the
        latest timestamp where the assignee node's value actually changed."""
        tiles = [c.tile for c in chosen_by_permit.values() if c is not None]
        tile_ids = [str(tile.pk) for tile in tiles]
        if not tile_ids:
            return {}

        node = (
            Node.objects.filter(
                graph__slug=GraphSlugs.PERMIT_APPLICATION,
                alias=PermitApplicationAliases.MINISTRY_ASSIGNEE,
            )
            .values("nodeid")
            .first()
        )
        if not node:
            return {}
        node_id = str(node["nodeid"])

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
        return {
            str(row["tileinstanceid"]): row["changed"].strftime("%B %d %Y")
            for row in rows
        }

    def _cards_to_json(self, permits, data: DashboardData):
        """Assemble a DashboardCard for each permit from the gathered lookups."""
        cards = []
        for permit in permits:
            cards.append(self._card_to_json(permit, data))
        return cards

    def _card_to_json(self, permit, data: DashboardData):
        """Assemble one permit's DashboardCard from its tiles and the gathered
        lookups. The full field mapping is documented on get_cards."""
        PA = PermitApplicationAliases
        aliased = permit.aliased_data
        # No unsatisfied requirement: label the CAP row complete and drill in to
        # the permit itself (there's no requirement to route to).
        requirement = data.chosen_by_permit.get(str(permit.pk)) or Requirement(
            name=self.ALL_SATISFIED_LABEL, route=str(permit.pk)
        )
        tile = requirement.tile
        identification = aliased.application_identification.aliased_data
        admin = aliased.application_admin.aliased_data

        # related_permit is cardinality-n, so descend with the helper for the first.
        related = self._node_value(aliased, PA.RELATED_PERMIT)
        related_permit_id = self._resource_id(related)
        hca = data.hca_permits.get(related_permit_id) or HcaPermit()
        holder_names = self._join_names(hca.holder_ids, data.contributor_names)

        assignee_id = tile and self._resource_id(tile.aliased_data.ministry_assignee)
        footer_name = data.contributor_names.get(assignee_id, "")
        footer_date = data.assignee_dates.get(str(tile.pk), "") if tile else ""

        # Leaving this in one spot for now so we can change it easier in the future.
        return DashboardCard(
            id=str(permit.pk),
            cap_label=requirement.name,
            cap_date=requirement.due_date,
            body_title=identification.project_name["display_value"],
            body_subtitle1=identification.application_id["display_value"],
            # industrial_sector is nested two groups deep, so keep the helper.
            body_subtitle2=self._node_value(aliased, PA.INDUSTRIAL_SECTOR).get(
                "display_value", ""
            ),
            body1="Permit: " + hca.number,
            body2="Permit holder: " + holder_names,
            body3="Project officer: " + "FillMeInWhenModelReady",
            body4=requirement.notes,
            body5="",
            footer_name=footer_name,
            footer_date=footer_date,
            route=requirement.route,
            urgency=0,
            cap_priority=admin.application_priority_level["display_value"],
        )
