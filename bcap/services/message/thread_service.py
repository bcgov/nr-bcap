"""Thread visibility, listings, unresolved counts, resolution and archives."""

import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.db.models import BooleanField, Case, CharField, Q, Value, When
from rest_framework.exceptions import PermissionDenied
from arches.app.models.models import TileModel
from arches.app.models.tile import Tile
from arches_querysets.models import ResourceTileTree

from bcap.permissions.permit_access import PermitAccess
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.services.message.message_context import (
    AUTHOR,
    RECIPIENT,
    MessageGraph as G,
    MessageViewer,
    ThreadRoot,
)
from bcap.util.aliases.bcap_message import BcapMessageAliases as A
from bcap.util.bcap_aliases import RESOURCE_ID
from bcap.util.dates import parse_iso_or_set_value
from bcap.util.graph import nodes_for
from bcap.util.tiles import (
    delete_tiles,
    references_any,
    resource_instance_id,
    resource_instance_value,
)

logger = logging.getLogger(__name__)


@dataclass
class ModuleUnresolved:
    """A process_module's unresolved thread count for the viewer."""

    module_id: str
    unresolved_count: int


class ThreadService:
    """Whole-thread visibility, listings and state (resolution, archive),
    separate from creating messages."""

    GATE_ALIASES = (A.RESOURCE_CONTEXT, A.THREAD)

    @classmethod
    def base_query(
        cls,
        viewer: MessageViewer,
        resource_ids=None,
        as_representation=True,
        aliases=None,
    ):
        """Every message the viewer may see, optionally limited to some resources
        and nodes. Staff see all; applicants see only external threads they are
        party to, on permits they or their company filed.

        Use as_representation=False before saving: represented references cannot
        be written back through the datatype."""
        queryset = ResourceTileTree.get_tiles(
            G.SLUG,
            resource_ids=resource_ids,
            as_representation=as_representation,
            nodes=(
                nodes_for(G.SLUG, [*aliases, *cls.GATE_ALIASES]) if aliases else None
            ),
        ).select_related("graph", "resource_instance_lifecycle_state")
        if viewer.staff:
            return queryset
        reachable = PermitAccess.own_or_company_resource_ids(viewer.user)
        return cls._limit_to_external_threads(queryset, viewer, reachable)

    def thread_roots_query(self, resource_ids, user, archived: bool = False):
        """The threads on readable resources, latest activity first, one row per
        root, annotated with the viewer's side. Shows the viewer's archived
        threads or their active ones."""
        resource_ids = [str(r) for r in resource_ids]
        for resource_id in resource_ids:
            PermitAccess.require_view(user, resource_id)
        viewer = MessageViewer.for_user(user)
        roots = (
            self.base_query(viewer).filter(
                resource_context__id__in=resource_ids, thread__isnull=True
            )
            # createdtime breaks ties on a null date.
            .order_by("-thread_last_message_date", "-createdtime")
        )
        roots = self._filter_by_archive(roots, viewer, archived)
        threads = G.roots(roots.values_list("pk", flat=True))
        sides = {root_id: viewer.thread_side(root) for root_id, root in threads.items()}
        needing_action = [
            root_id
            for root_id, root in threads.items()
            if self._needs_action(viewer, root, sides[root_id])
        ]
        # Computed in Python from the root tiles, so mapped on by pk.
        return roots.annotate(
            viewer_side=Case(
                *[When(pk=r, then=Value(side)) for r, side in sides.items() if side],
                default=Value(""),
                output_field=CharField(),
            ),
            viewer_needs_action=Case(
                When(pk__in=needing_action, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )

    def thread_messages_query(self, thread_id, user):
        """One thread's messages, newest first, gated on read access to the
        resource the thread hangs off."""
        PermitAccess.require_view(user, G.context_id(thread_id))
        return (
            self.base_query(MessageViewer.for_user(user)).filter(
                Q(pk=str(thread_id)) | Q(thread__id=str(thread_id))
            )
            # createdtime breaks ties on a null creation date.
            .order_by("-message_creation_date", "-createdtime")
        )

    @staticmethod
    def author_is_staff(message, user) -> bool:
        """Whether a thread message was written by staff or the Branch."""
        author = message.aliased_data.message_content.aliased_data.message_author
        author_id = resource_instance_id((author or {}).get("node_value"))
        return bool(author_id) and MessageViewer.for_user(user).is_staff_party(
            author_id
        )

    def unresolved_counts_by_module(
        self, submission_id, user
    ) -> list[ModuleUnresolved]:
        """The viewer's unresolved thread count for each module of a readable
        submission, summed over the module's requirements."""
        PermitAccess.require_view(user, str(submission_id))
        modules = ProcessRequirementService().module_requirement_ids(str(submission_id))
        counts = self._unresolved_counts(
            {rid for ids in modules.values() for rid in ids},
            MessageViewer.for_user(user),
        )
        return [
            ModuleUnresolved(
                module_id=module,
                unresolved_count=sum(counts.get(rid, 0) for rid in ids),
            )
            for module, ids in modules.items()
        ]

    def unresolved_counts_by_context(self, context_ids, username: str):
        """For each resource, how many of the viewer's active (unarchived)
        threads are still unresolved on the viewer's side."""
        user = get_user_model().objects.filter(username=username).first()
        if user is None:
            return {}
        return self._unresolved_counts(context_ids, MessageViewer.for_user(user))

    def _unresolved_counts(self, context_ids, viewer: MessageViewer):
        if not context_ids:
            return {}
        roots = self.base_query(
            viewer, as_representation=False, aliases=[A.RESOURCE_CONTEXT]
        ).filter(
            resource_context__id__in=[str(cid) for cid in context_ids],
            thread__isnull=True,
        )
        contexts = {
            str(root): str(context)
            for root, context in self._filter_by_archive(
                roots, viewer, archived=False
            ).values_list("pk", f"{A.RESOURCE_CONTEXT}__id")
        }
        return dict(
            Counter(
                contexts[root_id]
                for root_id, root in G.roots(contexts).items()
                if self._needs_action(viewer, root, viewer.thread_side(root))
            )
        )

    @staticmethod
    def _needs_action(viewer: MessageViewer, root: ThreadRoot, side):
        """Whether a thread awaits the viewer: they take part and their side is
        open. Whoever started it is only waiting on a reply until one comes."""
        if not side or not viewer.participates(root) or root.resolved[side]:
            return False
        return side == RECIPIENT or root.answered

    def update_thread_state(self, user, message_id, data):
        """Apply a PATCH body's "resolved" and "archived" flags, whichever are
        present, after one edit-access check on the parent resource."""
        PermitAccess.require_change(user, G.context_id(message_id))
        viewer = MessageViewer.for_user(user)
        self.set_viewer_resolution(message_id, data, viewer)
        self.set_viewer_archived(message_id, data, viewer)

    def set_viewer_resolution(self, message_id, data, viewer: MessageViewer):
        """Resolve or reopen the viewer's side of the thread. Does nothing when
        the body has no "resolved" flag; refuses a viewer not taking part."""
        if "resolved" not in data:
            return
        tile = self._root_tile(G.thread_id(message_id))
        side = viewer.thread_side(G.root(tile.data))
        if side is None:
            raise PermissionDenied("You are not on either side of this thread.")
        resolution = self._resolved_now_by(viewer) if data["resolved"] else None
        self._apply_resolutions(tile, {side: resolution})
        tile.save()

    def after_post(self, message_id, poster):
        """After a new message: date the thread by it, add the poster to the
        thread's participants unless they or a group of theirs already are, mark
        it answered if they are not on the starter's side, reopen the other
        side, resolve an applicant poster's own side (staff resolve theirs by
        hand), and bring the thread back for everyone who archived it."""
        viewer = MessageViewer.for_user(poster)
        thread_id = G.thread_id(message_id)
        tile = self._root_tile(thread_id)
        tile.data[G.node(A.THREAD_LAST_MESSAGE_DATE)] = G.content(message_id).get(
            G.node(A.MESSAGE_CREATION_DATE)
        )
        root = G.root(tile.data)
        if not viewer.participates(root):
            root.participants.add(str(viewer.contributor_id))
        tile.data[G.node(A.THREAD_PARTICIPANTS)] = [
            {RESOURCE_ID: p} for p in sorted(root.participants)
        ]
        side = viewer.thread_side(root)
        if side != AUTHOR:
            tile.data[G.node(A.THREAD_ANSWERED)] = True
        resolutions = {each: None for each in (AUTHOR, RECIPIENT) if each != side}
        if not viewer.staff:
            resolutions[side] = self._resolved_now_by(viewer)
        self._apply_resolutions(tile, resolutions)
        tile.save()
        delete_tiles(
            Tile.objects.filter(
                nodegroup_id=G.nodegroup(A.ARCHIVED_BY), resourceinstance_id=thread_id
            )
        )

    def set_viewer_archived(self, message_id, data, viewer: MessageViewer):
        """Archive or unarchive the thread for the viewer's contributor only. Does
        nothing when the body has no "archived" flag or the viewer has no
        contributor."""
        if "archived" not in data:
            return
        contributor_id = viewer.contributor_id
        if not contributor_id:
            logger.warning(
                "No Contributor for user %s; archive ignored.", viewer.user.id
            )
            return
        thread_id = G.thread_id(message_id)
        existing = G.archive_tiles(contributor_id, thread_id)
        if not data["archived"]:
            delete_tiles(existing)
            return
        if not existing.exists():
            Tile(
                resourceinstance_id=thread_id,
                nodegroup_id=G.nodegroup(A.ARCHIVED_BY),
                data={G.node(A.ARCHIVED_BY): resource_instance_value(contributor_id)},
            ).save()

    @staticmethod
    def _limit_to_external_threads(messages, viewer: MessageViewer, reachable):
        """Narrow messages to external threads on reachable resources whose root
        names the user or their company as author or recipient. A thread is kept
        or dropped whole."""
        parties = viewer.parties
        if not parties:
            logger.warning(
                "No Contributor for user %s; no messages visible.", viewer.user.id
            )
            return messages.none()
        # The allowed ids come from plain tile queries and the tree is narrowed
        # by pk: filtering the tree on its JSON-derived columns makes Postgres
        # recompute them for every message, which is what made this slow.
        link_node = G.node(A.THREAD)
        links = TileModel.objects.filter(
            nodegroup_id=G.nodegroup(A.THREAD), data__has_key=link_node
        ).exclude(**{f"data__{link_node}": None})
        root_ids = {
            str(pk)
            for pk in TileModel.objects.filter(
                references_any(G.node(A.MESSAGE_AUTHOR), parties)
                | references_any(G.node(A.RECIPIENT), parties),
                references_any(G.node(A.RESOURCE_CONTEXT), reachable),
                nodegroup_id=G.nodegroup(A.MESSAGE_AUTHOR),
            )
            .exclude(**{f"data__{G.node(A.IS_INTERNAL)}": True})
            .exclude(resourceinstance_id__in=links.values("resourceinstance_id"))
            .values_list("resourceinstance_id", flat=True)
        }
        reply_ids = links.filter(references_any(link_node, root_ids)).values(
            "resourceinstance_id"
        )
        return messages.filter(Q(pk__in=root_ids) | Q(pk__in=reply_ids))

    def _filter_by_archive(self, roots, viewer: MessageViewer, archived: bool):
        """Keep the roots the viewer has archived, or those they haven't."""
        if not viewer.contributor_id:
            return roots.none() if archived else roots
        archived_ids = G.archive_tiles(viewer.contributor_id).values_list(
            "resourceinstance_id", flat=True
        )
        if archived:
            return roots.filter(pk__in=archived_ids)
        return roots.exclude(pk__in=archived_ids)

    @staticmethod
    def _resolved_now_by(viewer: MessageViewer):
        """A (date, contributor id) resolution stamped now by the viewer."""
        now = parse_iso_or_set_value(datetime.now(timezone.utc).isoformat())
        return now, viewer.contributor_id

    @staticmethod
    def _root_tile(thread_id):
        """The thread root's content tile, saved directly rather than through
        the tree: saving the tree runs attachments through the file-list
        datatype, which deletes their stored files."""
        return Tile.objects.get(
            resourceinstance_id=thread_id, nodegroup_id=G.nodegroup(A.MESSAGE_AUTHOR)
        )

    @staticmethod
    def _apply_resolutions(tile, resolutions):
        """Write each side's resolution (or None to reopen) onto the root tile."""
        for side, resolution in resolutions.items():
            date_node, by_node = map(G.node, G.RESOLUTION_ALIASES[side])
            resolved_date, resolved_by = resolution or (None, None)
            tile.data[date_node] = resolved_date
            tile.data[by_node] = (
                [{RESOURCE_ID: str(resolved_by)}] if resolved_by else None
            )
