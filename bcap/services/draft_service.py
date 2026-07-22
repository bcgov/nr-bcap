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

from django.utils import timezone

from arches.app.models.models import (
    ResourceInstance,
    ResourceInstanceLifecycleState,
    TileModel,
)

from bcap.services.dashboard.base_graph_service import BaseGraphService
from bcap.util.aliases.drafts import DraftsAliases
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
    created: datetime | None = None
    # Stamped in place on every save (drafts have no edit log to derive it from).
    updated: datetime | None = None


class DraftService(BaseGraphService):
    """Owner-scoped CRUD over draft resources. All reads go through queryset() so
    the dashboard can page the same rows the API returns."""

    def queryset(self, user, graph_slug=None):
        """The user's drafts (superusers see all), oldest first. Filters by the
        target graph in SQL so callers can page without loading every draft."""
        qs = ResourceInstance.objects.filter(graph__slug=GraphSlugs.DRAFTS)
        if not user.is_superuser:
            qs = qs.filter(principaluser=user)
        if graph_slug is not None:
            nodeid, ngid = self._node_info(GraphSlugs.DRAFTS, DraftsAliases.GRAPH_SLUG)
            qs = qs.filter(
                tilemodel__nodegroup_id=ngid,
                **{f"tilemodel__data__{nodeid}": graph_slug},
            )
        return qs.order_by("createdtime").prefetch_related("tilemodel_set").distinct()

    def get(self, user, pk):
        """The user's draft with this id, or None if absent or not theirs."""
        return self.queryset(user).filter(pk=pk).first()

    def to_record(self, resource) -> DraftRecord:
        """Flatten a draft's tiles into the shape the API and dashboard read."""
        by_group = {str(t.nodegroup_id): t.data for t in resource.tilemodel_set.all()}

        def value(alias):
            nodeid, ngid = self._node_info(GraphSlugs.DRAFTS, alias)
            return (by_group.get(ngid) or {}).get(nodeid)

        blob = value(DraftsAliases.DRAFT_DATA)
        stamped = value(DraftsAliases.UPDATED_DATE)
        return DraftRecord(
            id=str(resource.pk),
            graph_slug=value(DraftsAliases.GRAPH_SLUG) or "",
            graph_publication_id=value(DraftsAliases.GRAPH_PUBLICATION_ID) or "",
            frontend_version=value(DraftsAliases.FRONTEND_VERSION) or "",
            parent_resource_id=value(DraftsAliases.PARENT_RESOURCE_ID) or "",
            data=json.loads(blob) if blob else {},
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
            graph_id=get_current_graph(GraphSlugs.DRAFTS).pk,
            principaluser=user,
            resource_instance_lifecycle_state=(
                ResourceInstanceLifecycleState.objects.first()
            ),
        )
        self._write(
            resource,
            {
                DraftsAliases.GRAPH_SLUG: graph_slug,
                DraftsAliases.GRAPH_PUBLICATION_ID: str(publication_id or ""),
                DraftsAliases.FRONTEND_VERSION: frontend_version or "",
                DraftsAliases.PARENT_RESOURCE_ID: str(parent_resource_id or ""),
                DraftsAliases.DRAFT_DATA: json.dumps(data or {}),
                DraftsAliases.UPDATED_DATE: timezone.now().isoformat(),
            },
        )
        return self.to_record(resource)

    def set_data(self, resource, data):
        """Replace a draft's blob with the caller's fully-merged data and
        re-stamp the save time."""
        now = timezone.now()
        self._write(
            resource,
            {
                DraftsAliases.DRAFT_DATA: json.dumps(data),
                DraftsAliases.UPDATED_DATE: now.isoformat(),
            },
        )
        # record() reads the resource's (now stale) prefetched tiles; only
        # draft_data/updated_date changed, so set them from what we just wrote.
        record = self.to_record(resource)
        record.data = data
        record.updated = now
        return record

    def _write(self, resource, values_by_alias):
        """Upsert each field's single-node tile, replacing its value in place."""
        for alias, value in values_by_alias.items():
            nodeid, ngid = self._node_info(GraphSlugs.DRAFTS, alias)
            TileModel.objects.update_or_create(
                resourceinstance=resource,
                nodegroup_id=ngid,
                defaults={"data": {nodeid: value}},
            )
