from dataclasses import replace
from itertools import chain

from django.db.models import (
    Exists,
    F,
    FloatField,
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

from bcap.util.graph import node_id, node_info, nodes_for
from bcap.services.dashboard.base_dashboard_service import BaseDashboardService
from bcap.services.dashboard.dashboard_types import (
    ApplicationCore,
    InternalDashboardData,
    DashboardFilter,
    InternalDashboardCard,
    InternalDashboardPage,
    InternalDashboardStatus,
    ModuleProgress,
    Requirement,
)
from bcap.services.bcap_service_request.bcap_service_request_service import (
    BcapServiceRequestService,
)
from bcap.services.message.thread_service import ThreadService
from bcap.util.aliases.bcap_service_request import BcapServiceRequestAliases
from bcap.util.aliases.process_requirement import ProcessRequirementAliases
from bcap.util.bcap_aliases import GraphSlugs, RESOURCE_ID
from bcap.util.queryset import filter_or_empty


class InternalDashboardService(BaseDashboardService):
    SR = BcapServiceRequestAliases
    PR = ProcessRequirementAliases

    CARD_NODES = [
        SR.PROJECT_NAME,
        SR.SERVICE_REQUEST_ID,
        SR.SERVICE_REQUEST_TYPE,
        SR.MODULE_ID,
        SR.MODULE_NAME,
        SR.MODULE_ORDER,
        SR.MODULE_COMPLETED_DATE,
        SR.IS_MODULE_COMPLETED,
    ]

    @classmethod
    def base_query(cls):
        """Submitted service requests still carrying an unsatisfied requirement,
        with the card's nodes (requirement tiles included) and the active
        assignee annotated. Staff-only route, so no narrowing by caller."""
        queryset = (
            ResourceTileTree.get_tiles(
                GraphSlugs.BCAP_SERVICE_REQUEST,
                nodes=nodes_for(
                    GraphSlugs.BCAP_SERVICE_REQUEST,
                    cls.CARD_NODES
                    + [
                        cls.SR.PROCESS_REQUIREMENT,
                        cls.SR.PROCESS_REQUIREMENT_ORDER,
                        cls.SR.MINISTRY_ASSIGNEE,
                    ],
                ),
                as_representation=True,
            )
            .select_related("graph")
            .order_by("pk")  # stable, so LIMIT/OFFSET pages don't overlap
        )
        queryset = queryset.annotate(
            active_assignee=cls._active_assignee_subquery(),
        )
        return queryset.filter(
            Exists(cls._submitted_tiles()),
            Exists(cls._active_requirement_tiles()),
        )

    def get_cards(
        self, query: DashboardFilter, username: str = ""
    ) -> InternalDashboardPage:
        """Build dashboard cards from BCAP Service Request resources and their
        related Process Requirement resources.

        Per-field mappings are documented as help_text on the card dataclass."""
        count, service_requests = self._permits(query, username)
        requirements_by_permit = self._requirement_tiles_by_permit(service_requests)
        # One traversal of the requirement tiles yields both the requirement ids
        # and the assignee ids the cards need.
        tiles = chain.from_iterable(requirements_by_permit.values())
        referenced = self._referenced_ids_by_alias(
            tiles, [self.SR.PROCESS_REQUIREMENT, self.SR.MINISTRY_ASSIGNEE]
        )
        chosen_by_permit = self._choose_requirements(
            requirements_by_permit, referenced[self.SR.PROCESS_REQUIREMENT]
        )
        data = InternalDashboardData(
            chosen_by_permit=chosen_by_permit,
            assignee_dates=self._assignee_change_dates(chosen_by_permit),
            hca_permits={},
            contributor_names=self._contributor_names(
                referenced[self.SR.MINISTRY_ASSIGNEE], {}
            ),
            unresolved_counts=self._unresolved_counts_by_permit(
                service_requests,
                username,
                self._requirement_ids_by_permit(requirements_by_permit),
            ),
        )
        return InternalDashboardPage(
            count=count,
            page=query.page,
            limit=query.limit,
            results=self._cards_to_json(service_requests, data),
        )

    @classmethod
    def _submitted_tiles(cls):
        """Per-service-request subquery of its service_request_admin tile once
        the submission date is filled in."""
        date_id, admin_ng = node_info(
            GraphSlugs.BCAP_SERVICE_REQUEST, cls.SR.APPLICATION_SUBMISSION_DATE
        )
        return (
            TileModel.objects.filter(
                resourceinstance_id=OuterRef("pk"), nodegroup_id=admin_ng
            )
            .annotate(submission_date=KeyTextTransform(date_id, "data"))
            .exclude(submission_date__isnull=True)
            .exclude(submission_date="")
        )

    def _permits(self, query, username=""):
        """The query's page of service requests and the total count."""
        queryset = self._filter_by_status(self.base_query(), query.status, username)
        return self._page(queryset, query)

    def _filter_by_status(self, queryset, status, username):
        """Narrow service requests by the active requirement's ministry_assignee."""
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

    @classmethod
    def _active_assignee_subquery(cls):
        """Per service request, the ministry_assignee id of its active
        requirement."""
        return Subquery(cls._active_requirement_tiles().values("assignee")[:1])

    @classmethod
    def _active_requirement_tiles(cls):
        """Per-service-request subquery of its unsatisfied process_requirement
        tiles, ordered by module then requirement order (the first unsatisfied
        wins). The non-null guard stays in lockstep with _choose_requirements."""
        sr, req = GraphSlugs.BCAP_SERVICE_REQUEST, GraphSlugs.PROCESS_REQUIREMENT
        order_id, child_ng = node_info(sr, cls.SR.PROCESS_REQUIREMENT_ORDER)
        assignee_id = node_id(sr, cls.SR.MINISTRY_ASSIGNEE)
        requirement_id = node_id(sr, cls.SR.PROCESS_REQUIREMENT)
        module_order_id = node_id(sr, cls.SR.MODULE_ORDER)
        status_id, status_ng = node_info(req, cls.PR.REQUIREMENT_STATUS)

        def get_json_resource_id(node_id):
            return KeyTextTransform(
                RESOURCE_ID, KeyTransform("0", KeyTransform(node_id, "data"))
            )

        module_order = Subquery(
            TileModel.objects.filter(tileid=OuterRef("parenttile_id"))
            .annotate(
                value=Cast(KeyTextTransform(module_order_id, "data"), FloatField())
            )
            .values("value")[:1]
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
                module_order_value=module_order,
                order_value=Cast(KeyTextTransform(order_id, "data"), FloatField()),
            )
            .exclude(requirement__in=satisfied_ids)
            .filter(requirement__isnull=False)
            .order_by("module_order_value", "order_value")
        )

    def _requirement_tiles_by_permit(self, service_requests):
        """Map service request id -> its process_requirement tiles, sorted by
        the parent module's order then the requirement's own order. Read from
        the already-loaded tree (see the base query), so no query."""
        requirements_by_permit = {}
        for sr in service_requests:
            ordered = []
            for admin in self._nested_tiles(sr.aliased_data.service_request_admin):
                for module in self._nested_tiles(admin.aliased_data.process_module):
                    module_order = self._order_value(module.aliased_data.module_order)
                    for tile in self._nested_tiles(
                        module.aliased_data.process_requirement
                    ):
                        requirement_order = self._order_value(
                            tile.aliased_data.process_requirement_order
                        )
                        ordered.append((module_order, requirement_order, tile))
            ordered.sort(key=lambda row: (row[0], row[1]))
            requirements_by_permit[str(sr.pk)] = [row[2] for row in ordered]
        return requirements_by_permit

    def _requirement_ids_by_permit(self, requirements_by_permit):
        """Map service request id -> the set of process_requirement resource ids
        its tiles reference, read off the already-loaded tree."""
        return {
            sr_id: self._referenced_ids(tiles, self.SR.PROCESS_REQUIREMENT)
            for sr_id, tiles in requirements_by_permit.items()
        }

    def _contributor_names(self, assignee_ids, hca_permits):
        """Map id -> display name for every Contributor a card references."""
        return {c.id: c.name for c in self.contributors.by_ids(set(assignee_ids))}

    def _choose_requirements(self, requirements_by_permit, requirement_ids):
        """Map service request id -> Requirement: per service request, the
        unsatisfied requirement whose tile has the lowest
        process_requirement_order, or None when every requirement is satisfied."""
        requirements = self._requirements_by_id(requirement_ids)

        chosen = {}
        for sr_id, tiles in requirements_by_permit.items():
            chosen[sr_id] = None
            for tile in tiles:
                requirement_id = self._resource_id(
                    tile.aliased_data.process_requirement
                )
                requirement = requirements.get(requirement_id)
                if requirement:
                    chosen[sr_id] = replace(requirement, tile=tile)
                    break
        return chosen

    def _requirements_by_id(self, requirement_ids):
        """Map requirement resource id -> Requirement, for the unsatisfied ones."""
        node_ids, nodegroups = {}, set()
        for alias in (
            self.PR.REQUIREMENT_STATUS,
            self.PR.REQUIREMENT_NAME,
            self.PR.REQUIREMENT_PROCESS_DUE_DATE,
            self.PR.ASSESSMENT_NOTES,
        ):
            node_ids[alias], nodegroup = node_info(
                GraphSlugs.PROCESS_REQUIREMENT, alias
            )
            nodegroups.add(nodegroup)

        data_by_requirement = {str(rid): {} for rid in requirement_ids}
        rows = TileModel.objects.filter(
            resourceinstance_id__in=requirement_ids, nodegroup_id__in=nodegroups
        ).values_list("resourceinstance_id", "data")
        for resource_id, data in rows:
            data_by_requirement[str(resource_id)].update(data)

        def text(data, alias):
            return self.display_text(data.get(node_ids[alias]))

        return {
            requirement_id: Requirement(
                name=text(data, self.PR.REQUIREMENT_NAME),
                due_date=text(data, self.PR.REQUIREMENT_PROCESS_DUE_DATE),
                route=requirement_id,
                notes=text(data, self.PR.ASSESSMENT_NOTES),
            )
            for requirement_id, data in data_by_requirement.items()
            if not data.get(node_ids[self.PR.REQUIREMENT_STATUS])
        }

    @staticmethod
    def _order_value(value):
        """An order node's value as a sort key; a missing or unset order sorts
        last (infinity) so a tile that has one always wins."""
        if not value or value["node_value"] is None:
            return float("inf")
        return value["node_value"]

    def _assignee_change_dates(self, chosen_by_permit):
        """Map requirement-tile id -> date its ministry_assignee last changed,
        read from the edit log."""
        tiles = [c.tile for c in chosen_by_permit.values() if c is not None]
        tile_ids = [str(tile.pk) for tile in tiles]
        if not tile_ids:
            return {}

        assignee_node = node_id(
            GraphSlugs.BCAP_SERVICE_REQUEST, self.SR.MINISTRY_ASSIGNEE
        )

        def assignee(column):
            return Coalesce(
                KeyTextTransform(assignee_node, column),
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

    def _application_core(self, aliased) -> ApplicationCore:
        """The service-request card fields common to both dashboards."""

        def display(alias):
            return self.node_value(aliased, alias).get("display_value", "") or ""

        return ApplicationCore(
            project_name=display(self.SR.PROJECT_NAME),
            application_number=display(self.SR.SERVICE_REQUEST_ID),
            submission_type=display(self.SR.SERVICE_REQUEST_TYPE),
            industrial_sector="",
            priority_level="",
            organization="",
            related_permit_id=None,
        )

    def _module_progress(self, service_request) -> ModuleProgress:
        """How many modules are complete, and the lowest-ordered one still
        outstanding. Read off the loaded tree, so no query."""
        modules = sorted(
            (
                module.aliased_data
                for admin in self._nested_tiles(
                    service_request.aliased_data.service_request_admin
                )
                for module in self._nested_tiles(admin.aliased_data.process_module)
            ),
            key=lambda data: self._raw_value(data, self.SR.MODULE_ORDER) or 0,
        )
        outstanding = [
            data
            for data in modules
            if not self._raw_value(data, self.SR.IS_MODULE_COMPLETED)
        ]
        return ModuleProgress(
            current_module=(
                self.display_text(self.node_value(outstanding[0], self.SR.MODULE_NAME))
                if outstanding
                else ""
            ),
            completed=len(modules) - len(outstanding),
            total=len(modules),
        )

    def _unresolved_counts_by_permit(
        self, service_requests, username, requirements_by_permit=None
    ):
        """Unresolved thread counts keyed by service request id."""
        contexts = (
            BcapServiceRequestService().submission_context_ids_for_service_requests(
                service_requests, requirements_by_permit
            )
        )
        counts = ThreadService().unresolved_counts_by_context(
            set(chain.from_iterable(contexts.values())), username
        )
        return {
            sr_id: sum(counts.get(cid, 0) for cid in context_ids)
            for sr_id, context_ids in contexts.items()
        }

    def _cards_to_json(self, service_requests, data: InternalDashboardData):
        """A card for each service request, assembled from the gathered lookups."""
        cards = []
        for sr in service_requests:
            if data.chosen_by_permit.get(str(sr.pk)) is not None:
                card = self._card_to_json(sr, data)
                card.module_progress = self._module_progress(sr)
                cards.append(card)
        return cards

    def _card_to_json(self, service_request, data: InternalDashboardData):
        """Assemble one service request's card from its tiles and the gathered
        lookups."""
        aliased = service_request.aliased_data
        requirement = data.chosen_by_permit[str(service_request.pk)]
        tile = requirement.tile
        core = self._application_core(aliased)

        assignee_id = self._resource_id(tile.aliased_data.ministry_assignee)
        ministry_assignee_name = data.contributor_names.get(assignee_id, "")
        ministry_assignee_change_date = data.assignee_dates.get(str(tile.pk), "")
        unresolved_messages = data.unresolved_counts.get(str(service_request.pk), 0)

        return InternalDashboardCard(
            id=str(service_request.pk),
            requirement_name=requirement.name,
            requirement_due_date=requirement.due_date,
            project_name=core.project_name,
            application_number=core.application_number,
            submission_type=core.submission_type,
            assessment_notes=requirement.notes,
            ministry_assignee_name=ministry_assignee_name,
            ministry_assignee_id=assignee_id,
            ministry_assignee_change_date=ministry_assignee_change_date,
            requirement_id=requirement.route,
            urgency=0,
            unresolved_messages=unresolved_messages,
        )
