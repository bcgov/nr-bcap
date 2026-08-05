"""Draft storage as resources of the standalone 'drafts' graph, one JSON blob
per draft. The blob lives in one draft_data node, updated in place, so only the
current version is ever stored. Reads hand back the ordinary arches-querysets
representation, which record() flattens to the shape the API and dashboard read.
Every node but the blob itself is searchable, so saves index like any other
resource."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from arches.app.models.models import ResourceInstance, TileModel

from arches_querysets.models import ResourceTileTree, TileTree

from bcap.services.contributor.organization_service import OrganizationService
from bcap.services.dashboard.base_graph_service import BaseGraphService
from bcap.util.aliases.workflow_drafts import (
    WorkflowDraftsAliases,
    WorkflowDraftsGroupAliases,
)
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import get_current_graph, node_info
from bcap.util.tiles import resource_instance_id, resource_instance_value


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
    updated: str = ""


class WorkflowDraftService(BaseGraphService):
    """CRUD over draft resources, scoped to the caller's company. Reads and the
    lookups behind the writes both go through queryset(), so a colleague can
    resume and delete a draft as well as see it."""

    def queryset(self, user, graph_slug=None, parent_resource_id=None, own_only=False):
        """A user's drafts and their associated companies', oldest first; branch
        staff get no widening. own_only narrows to the ones the user created.
        Graph and parent filter in SQL, so no caller loads them all."""
        qs = ResourceTileTree.get_tiles(
            GraphSlugs.WORKFLOW_DRAFTS, as_representation=True
        )
        if own_only:
            qs = qs.filter(principaluser=user)
        else:
            qs = qs.filter(
                OrganizationService().visible_to(
                    user, WorkflowDraftsAliases.OWNING_ORGANIZATION
                )
            )
        if graph_slug is not None:
            qs = qs.filter(**{WorkflowDraftsAliases.GRAPH_SLUG: graph_slug})
        if parent_resource_id:
            qs = qs.filter(
                **{
                    f"{WorkflowDraftsAliases.PARENT_RESOURCE}__contains": (
                        resource_instance_value(parent_resource_id)
                    )
                }
            )
        return qs.select_related("principaluser").order_by("createdtime")

    def get(self, user, pk):
        """The draft with this id as far as the user can see it, or None."""
        return self.queryset(user).filter(pk=pk).first()

    def create(
        self,
        user,
        graph_slug,
        data,
        publication_id="",
        frontend_version="",
        parent_resource_id="",
        organization_id="",
    ):
        """Create a draft owned by the user, stamping the graph publication, the
        organization whose members may see it, and the save time. The caller
        settles which organization that is (see organization_to_stamp)."""
        draft = ResourceTileTree(
            graph_id=get_current_graph(GraphSlugs.WORKFLOW_DRAFTS).pk,
            **{
                WorkflowDraftsGroupAliases.SYSTEM_INFO: {
                    WorkflowDraftsAliases.GRAPH_SLUG: graph_slug,
                    WorkflowDraftsAliases.GRAPH_PUBLICATION_ID: str(
                        publication_id or ""
                    ),
                    WorkflowDraftsAliases.FRONTEND_VERSION: frontend_version or "",
                    WorkflowDraftsAliases.OWNING_ORGANIZATION: (
                        resource_instance_value(organization_id)
                    ),
                },
                # Empty: the tile is created here so it exists, but the blob
                # itself is written past the audit below.
                WorkflowDraftsGroupAliases.DRAFT_PAYLOAD: {
                    WorkflowDraftsAliases.DRAFT_DATA: "{}",
                },
                WorkflowDraftsGroupAliases.FILING_INFO: {
                    WorkflowDraftsAliases.PARENT_RESOURCE: (
                        resource_instance_value(parent_resource_id)
                    ),
                    WorkflowDraftsAliases.UPDATED_DATE: datetime.now(
                        timezone.utc
                    ).isoformat(),
                },
            },
        )
        draft.save(user=user, force_admin=True, partial=False, index=True)
        ResourceInstance.objects.filter(pk=draft.pk).update(principaluser=user)
        self._write_blob_no_audit(draft.pk, data or {})
        return self.queryset(user, own_only=True).filter(pk=draft.pk).first()

    def set_data(self, user, pk, data, current_step=None):
        """Replace a draft's blob with the caller's fully-merged data and
        re-stamp the save time. Pass current_step to move the step marker too;
        omit it to leave the stored one alone."""
        tile = TileTree.get_tiles(
            GraphSlugs.WORKFLOW_DRAFTS,
            WorkflowDraftsGroupAliases.FILING_INFO,
            resource_ids=[pk],
        ).get()

        filing = tile.aliased_data
        filing.updated_date = datetime.now(timezone.utc).isoformat()
        if current_step is not None:
            filing.current_step = current_step
        tile.save(user=user, force_admin=True, partial=True, index=True)

        self._write_blob_no_audit(pk, data)
        return self.get(user, pk)

    @classmethod
    def _write_blob_no_audit(cls, pk, data):
        """Store the blob straight onto its tile, past the audit: a tile save
        archives a copy of the whole form on every write."""
        nodeid, ngid = node_info(
            GraphSlugs.WORKFLOW_DRAFTS, WorkflowDraftsAliases.DRAFT_DATA
        )
        TileModel.objects.filter(resourceinstance_id=pk, nodegroup_id=ngid).update(
            data={nodeid: json.dumps(data, indent=2)}
        )

    @classmethod
    def record(cls, resource):
        """A draft resource flattened to the record the API returns."""

        def field(alias):
            return cls._raw_value(resource.aliased_data, alias) or ""

        return DraftRecord(
            id=str(resource.pk),
            graph_slug=field(WorkflowDraftsAliases.GRAPH_SLUG),
            graph_publication_id=field(WorkflowDraftsAliases.GRAPH_PUBLICATION_ID),
            frontend_version=field(WorkflowDraftsAliases.FRONTEND_VERSION),
            parent_resource_id=cls.parent_id(resource),
            data=cls.blob(resource),
            current_step=field(WorkflowDraftsAliases.CURRENT_STEP),
            created=resource.createdtime,
            updated=field(WorkflowDraftsAliases.UPDATED_DATE),
        )

    @classmethod
    def parent_id(cls, resource):
        """The id of the resource a draft was started from, or ""."""
        return resource_instance_id(
            cls._raw_value(resource.aliased_data, WorkflowDraftsAliases.PARENT_RESOURCE)
        )

    @classmethod
    def blob(cls, resource):
        """The stored draft blob of a resource read back from queryset()."""
        raw = cls._raw_value(resource.aliased_data, WorkflowDraftsAliases.DRAFT_DATA)
        return json.loads(raw) if raw else {}
