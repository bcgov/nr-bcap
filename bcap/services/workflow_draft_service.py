"""Draft storage as resources of the standalone 'drafts' graph, one JSON blob
per draft. Written with the raw ORM (ResourceInstance/TileModel), not the
Resource/Tile proxy, so drafts never hit the edit log or the search index: a
draft is scratch data re-saved on every keystroke, and auditing it would copy
the whole blob into edit_log on each save. The blob lives in one draft_data
tile, updated in place, so only the current version is ever stored."""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from django.db.models import Exists, OuterRef
from django.utils import timezone

from arches.app.models.models import (
    ResourceInstance,
    ResourceInstanceLifecycleState,
    TileModel,
)
from arches.app.models.resource import Resource

from bcap.services.dashboard.base_graph_service import BaseGraphService
from bcap.util.aliases.workflow_drafts import WorkflowDraftsAliases
from bcap.util.auth.groups import is_internal_user
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import get_current_graph


@dataclass
class DraftRecord:
    """A draft flattened out of its tiles, the shape the API and dashboard read."""

    id: str
    graph_slug: str
    graph_publication_id: str
    frontend_version: str
    # The resource the draft was started from, so that resource's page can list
    # its own drafts. Empty when the draft has no parent.
    parent_resource_id: str = ""
    data: dict = field(default_factory=dict)
    current_step: str = ""
    created: datetime | None = None
    # Stamped in place on every save (drafts have no edit log to derive it from).
    updated: datetime | None = None


class WorkflowDraftService(BaseGraphService):
    """CRUD over draft resources, scoped to the reader. All reads go through
    queryset() so the dashboard can page the same rows the API returns."""

    def queryset(self, user, graph_slug=None, parent_resource_id=None):
        """An applicant's own drafts, oldest first; branch staff see everyone's.
        Graph and parent filter in SQL, so no caller loads them all."""
        qs = ResourceInstance.objects.filter(graph__slug=GraphSlugs.WORKFLOW_DRAFTS)
        if not is_internal_user(user):
            qs = qs.filter(principaluser=user)
        if graph_slug is not None:
            qs = qs.filter(self._has_tile(WorkflowDraftsAliases.GRAPH_SLUG, graph_slug))
        if parent_resource_id:
            qs = qs.filter(
                self._has_tile(
                    WorkflowDraftsAliases.PARENT_RESOURCE,
                    self._resource_instance_value(parent_resource_id),
                    lookup="contains",
                )
            )
        return qs.order_by("createdtime").prefetch_related("tilemodel_set")

    def _has_tile(self, alias, value, lookup="exact"):
        """Condition matching drafts whose tile for this alias holds the value.
        A subquery rather than a join, so two of them don't multiply rows (and
        the whole queryset needs no distinct() to put them back)."""
        nodeid, ngid = self._node_info(GraphSlugs.WORKFLOW_DRAFTS, alias)
        return Exists(
            TileModel.objects.filter(
                resourceinstance=OuterRef("pk"),
                nodegroup_id=ngid,
                **{f"data__{nodeid}__{lookup}": value},
            )
        )

    def get(self, user, pk):
        """The draft with this id as far as the user can see it, or None."""
        return self.queryset(user).filter(pk=pk).first()

    def to_record(self, resource) -> DraftRecord:
        """Flatten a draft's tiles into the shape the API and dashboard read."""
        by_group = {str(t.nodegroup_id): t.data for t in resource.tilemodel_set.all()}

        def value(alias):
            nodeid, ngid = self._node_info(GraphSlugs.WORKFLOW_DRAFTS, alias)
            return (by_group.get(ngid) or {}).get(nodeid)

        blob = value(WorkflowDraftsAliases.DRAFT_DATA)
        stamped = value(WorkflowDraftsAliases.UPDATED_DATE)
        return DraftRecord(
            id=str(resource.pk),
            graph_slug=value(WorkflowDraftsAliases.GRAPH_SLUG) or "",
            graph_publication_id=value(WorkflowDraftsAliases.GRAPH_PUBLICATION_ID)
            or "",
            frontend_version=value(WorkflowDraftsAliases.FRONTEND_VERSION) or "",
            parent_resource_id=self._resource_id_from(
                value(WorkflowDraftsAliases.PARENT_RESOURCE)
            ),
            data=json.loads(blob) if blob else {},
            current_step=value(WorkflowDraftsAliases.CURRENT_STEP) or "",
            created=resource.createdtime,
            updated=datetime.fromisoformat(stamped) if stamped else None,
        )

    def create(
        self,
        user,
        graph_slug,
        data,
        publication_id="",
        frontend_version="",
        parent_resource_id="",
    ):
        """Create a draft owned by the user, stamping the graph publication and
        save time, and return the flattened result."""
        resource = ResourceInstance.objects.create(
            resourceinstanceid=uuid.uuid4(),
            graph_id=get_current_graph(GraphSlugs.WORKFLOW_DRAFTS).pk,
            principaluser=user,
            resource_instance_lifecycle_state=(
                ResourceInstanceLifecycleState.objects.first()
            ),
        )
        self._write(
            resource,
            {
                WorkflowDraftsAliases.GRAPH_SLUG: graph_slug,
                WorkflowDraftsAliases.GRAPH_PUBLICATION_ID: str(publication_id or ""),
                WorkflowDraftsAliases.FRONTEND_VERSION: frontend_version or "",
                WorkflowDraftsAliases.PARENT_RESOURCE: self._resource_instance_value(
                    parent_resource_id
                ),
                WorkflowDraftsAliases.DRAFT_DATA: json.dumps(data or {}),
                WorkflowDraftsAliases.UPDATED_DATE: timezone.now().isoformat(),
            },
        )
        # Other resources reference a draft (a message's resource_context points
        # at it), and arches dereferences descriptors when building those names.
        # Build them once here so a draft never has a null descriptor.
        Resource.objects.get(pk=resource.pk).save_descriptors()
        return self.to_record(resource)

    def set_data(self, resource, data, current_step=None):
        """Replace a draft's blob with the caller's fully-merged data and
        re-stamp the save time. Pass current_step to move the step marker too;
        omit it to leave the stored one alone."""
        now = timezone.now()
        values = {
            WorkflowDraftsAliases.DRAFT_DATA: json.dumps(data),
            WorkflowDraftsAliases.UPDATED_DATE: now.isoformat(),
        }
        if current_step is not None:
            values[WorkflowDraftsAliases.CURRENT_STEP] = current_step
        self._write(resource, values)
        resource.refresh_from_db()
        return self.to_record(resource)

    @staticmethod
    def _resource_instance_value(resource_id):
        """A resource-instance node value (a one-element list) for a parent id, or
        an empty list when the draft has no parent."""
        return [{"resourceId": str(resource_id)}] if resource_id else []

    @staticmethod
    def _resource_id_from(node_value):
        """The parent resource id out of a resource-instance node value, tolerating
        a legacy bare string from before parent_resource became resource-instance."""
        if isinstance(node_value, list):
            return node_value[0]["resourceId"] if node_value else ""
        return node_value or ""

    def _write(self, resource, values_by_alias):
        """Upsert each field's single-node tile, replacing its value in place."""
        for alias, value in values_by_alias.items():
            nodeid, ngid = self._node_info(GraphSlugs.WORKFLOW_DRAFTS, alias)
            TileModel.objects.update_or_create(
                resourceinstance=resource,
                nodegroup_id=ngid,
                defaults={"data": {nodeid: value}},
            )
