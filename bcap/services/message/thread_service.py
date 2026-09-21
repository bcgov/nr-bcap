"""Thread visibility, listings, unresolved counts, resolution and archives."""

import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.db.models import (
    BooleanField,
    Case,
    CharField,
    DateTimeField,
    Q,
    Value,
    When,
)
from rest_framework.exceptions import PermissionDenied
from arches.app.models.models import TileModel
from arches.app.models.tile import Tile
from arches_querysets.models import ResourceTileTree

from bcap.permissions.groups import is_internal_user
from bcap.permissions.permit_access import PermitAccess
from bcap.services.contributor.contributor_service import ContributorService
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.services.message.message_context import (
    AUTHOR,
    RECIPIENT,
    MessageGraph as G,
    MessageViewer,
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
from bcap.util.user import user_log_id

logger = logging.getLogger(__name__)


@dataclass
class ModuleUnresolved:
    """A process_module's unresolved thread count for the viewer."""

    module_id: str
    unresolved_count: int


class ThreadService:
    """Whole-thread visibility, listings and state (resolution, archive),
    separate from creating messages."""

    GATE_ALIASES = (A.RESOURCE_CONTEXT, A.RELATED_SOURCE_MESSAGE)

    @classmethod
    def base_query(cls, user, resource_ids=None, as_representation=True, aliases=None):
        """Every message the user may see, optionally limited to some resources
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
        if is_internal_user(user):
            return queryset
        reachable = PermitAccess.own_or_company_resource_ids(user)
        return cls._limit_to_external_threads(queryset, user, reachable)

    def thread_roots_query(self, resource_id, user, archived=False):
        """The threads on a readable resource, newest first, one row per root,
        annotated with the latest message date and the viewer's side. Shows the
        viewer's archived threads or their active ones."""
        PermitAccess.require_view(user, str(resource_id))
        viewer = MessageViewer(user)
        roots = (
            self.base_query(user).filter(
                resource_context__id=str(resource_id),
                related_source_message__isnull=True,
            )
            # createdtime breaks ties on a null creation date.
            .order_by("-message_creation_date", "-createdtime")
        )
        roots = self._filter_by_archive(roots, viewer, archived)
        latest, sides = self._latest_dates_and_sides(resource_id, viewer)
        # A subquery annotation can't reach these: the thread link is a JSON node,
        # not a column an OuterRef can compare against, so map them on by pk.
        return roots.annotate(
            last_message_date=Case(
                *[When(pk=r, then=Value(dt)) for r, dt in latest.items()],
                default=None,
                output_field=DateTimeField(),
            ),
            viewer_side=Case(
                *[When(pk=r, then=Value(side)) for r, side in sides.items() if side],
                default=Value(""),
                output_field=CharField(),
            ),
            # Staff resolve by hand; an applicant's side resolves as they read.
            viewer_is_staff=Value(viewer.staff, output_field=BooleanField()),
        )

    def thread_messages_query(self, thread_id, user):
        """One thread's messages, oldest first, gated on read access to the
        resource the thread hangs off."""
        PermitAccess.require_view(user, G.context_id(thread_id))
        return (
            self.base_query(user).filter(
                Q(pk=str(thread_id)) | Q(related_source_message__id=str(thread_id))
            )
            # createdtime breaks ties on a null creation date.
            .order_by("message_creation_date", "createdtime")
        )

    def unresolved_counts_by_module(
        self, submission_id, user
    ) -> list[ModuleUnresolved]:
        """The viewer's unresolved thread count for each module of a readable
        submission, summed over the module's requirements."""
        PermitAccess.require_view(user, str(submission_id))
        modules = ProcessRequirementService().module_requirement_ids(str(submission_id))
        counts = self.unresolved_counts_by_context(
            {rid for ids in modules.values() for rid in ids}, user.username
        )
        return [
            ModuleUnresolved(
                module_id=module,
                unresolved_count=sum(counts.get(rid, 0) for rid in ids),
            )
            for module, ids in modules.items()
        ]

    def unresolved_counts_by_context(self, context_ids, username):
        """For each resource, how many of the viewer's active (unarchived)
        threads are still unresolved on the viewer's side."""
        if not context_ids:
            return {}
        user = get_user_model().objects.filter(username=username).first()
        if user is None:
            return {}
        viewer = MessageViewer(user)
        roots = self.base_query(
            user,
            as_representation=False,
            aliases=[
                A.MESSAGE_AUTHOR,
                A.RECIPIENT,
                A.AUTHOR_RESOLVED_DATE,
                A.RECIPIENT_RESOLVED_DATE,
            ],
        ).filter(
            resource_context__id__in=[str(cid) for cid in context_ids],
            related_source_message__isnull=True,
        )
        rows = self._filter_by_archive(roots, viewer, archived=False).values_list(
            f"{A.RESOURCE_CONTEXT}__id",
            f"{A.MESSAGE_AUTHOR}__id",
            f"{A.RECIPIENT}__id",
            A.AUTHOR_RESOLVED_DATE,
            A.RECIPIENT_RESOLVED_DATE,
        )
        counts = Counter()
        for context_id, author_id, recipient_id, author_date, recipient_date in rows:
            side = viewer.side_of(author_id, recipient_id)
            if (side == AUTHOR and not author_date) or (
                side == RECIPIENT and not recipient_date
            ):
                counts[str(context_id)] += 1
        return dict(counts)

    def update_thread_state(self, user, message_id, data):
        """Apply a PATCH body's "resolved" and "archived" flags, whichever are
        present, after one edit-access check on the parent resource."""
        PermitAccess.require_change(user, G.context_id(message_id))
        self.set_viewer_resolution(message_id, data, user)
        self.set_viewer_archived(message_id, data, user.username)

    def set_viewer_resolution(self, message_id, data, user):
        """Resolve or reopen the viewer's side of the thread. Does nothing when
        the body has no "resolved" flag; refuses a viewer on neither side."""
        if "resolved" not in data:
            return
        viewer = MessageViewer(user)
        thread_id = G.thread_id(message_id)
        side = viewer.side_of(*self._root_author_and_recipient(thread_id))
        if side is None:
            raise PermissionDenied("You are not on either side of this thread.")
        self._save_resolutions(
            thread_id,
            {side: self._resolved_now_by(viewer) if data["resolved"] else None},
        )

    def update_resolutions_after_post(self, message_id, poster):
        """After a new message: reopen the other side (both sides if the poster
        is on neither). An applicant's own side resolves too; staff resolve
        theirs by hand."""
        viewer = MessageViewer(poster)
        thread_id = G.thread_id(message_id)
        side = viewer.side_of(*self._root_author_and_recipient(thread_id))
        resolutions = {each: None for each in (AUTHOR, RECIPIENT) if each != side}
        if side and not viewer.staff:
            resolutions[side] = self._resolved_now_by(viewer)
        self._save_resolutions(thread_id, resolutions)

    def set_viewer_archived(self, message_id, data, username):
        """Archive or unarchive the thread for this user's contributor only. Does
        nothing when the body has no "archived" flag or the user has no
        contributor."""
        if "archived" not in data:
            return
        contributor_id = ContributorService().username_contributor_id(username)
        if not contributor_id:
            logger.warning(
                "No Contributor for user %s; archive ignored.",
                user_log_id(username),
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

    def unarchive_for_everyone(self, message_id):
        """Clear every viewer's archive of a message's thread, so a new reply
        brings it back for all. No-op for a new thread."""
        delete_tiles(
            Tile.objects.filter(
                nodegroup_id=G.nodegroup(A.ARCHIVED_BY),
                resourceinstance_id=G.thread_id(message_id),
            )
        )

    @staticmethod
    def _limit_to_external_threads(messages, user, reachable):
        """Narrow messages to external threads on reachable resources whose root
        names the user or their company as author or recipient. A thread is kept
        or dropped whole."""
        parties = MessageViewer.party_ids(user)
        if not parties:
            logger.warning("No Contributor for user %s; no messages visible.", user.id)
            return messages.none()
        # The allowed ids come from plain tile queries and the tree is narrowed
        # by pk: filtering the tree on its JSON-derived columns makes Postgres
        # recompute them for every message, which is what made this slow.
        link_node = G.node(A.RELATED_SOURCE_MESSAGE)
        links = TileModel.objects.filter(
            nodegroup_id=G.nodegroup(A.RELATED_SOURCE_MESSAGE), data__has_key=link_node
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

    def _latest_dates_and_sides(self, resource_id, viewer):
        """For each thread on the resource: its latest message date, and the
        viewer's side of it."""
        rows = (
            self.base_query(
                viewer.user,
                as_representation=False,
                aliases=[A.MESSAGE_CREATION_DATE, A.MESSAGE_AUTHOR, A.RECIPIENT],
            )
            .filter(resource_context__id=str(resource_id))
            .values_list(
                "pk",
                f"{A.RELATED_SOURCE_MESSAGE}__id",
                A.MESSAGE_CREATION_DATE,
                f"{A.MESSAGE_AUTHOR}__id",
                f"{A.RECIPIENT}__id",
            )
        )
        latest, sides = {}, {}
        for message_id, thread_id, date, author_id, recipient_id in rows:
            root_id = str(thread_id or message_id)
            if date and (root_id not in latest or date > latest[root_id]):
                latest[root_id] = date
            if not thread_id:
                sides[root_id] = viewer.side_of(author_id, recipient_id)
        return latest, sides

    def _filter_by_archive(self, roots, viewer, archived):
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
    def _root_author_and_recipient(thread_id):
        """A thread root's (author id, recipient id)."""
        content = G.content(thread_id)
        return (
            resource_instance_id(content.get(G.node(A.MESSAGE_AUTHOR))),
            resource_instance_id(content.get(G.node(A.RECIPIENT))),
        )

    @staticmethod
    def _resolved_now_by(viewer):
        """A (date, contributor id) resolution stamped now by the viewer."""
        now = parse_iso_or_set_value(datetime.now(timezone.utc).isoformat())
        return now, viewer.contributor_id

    @staticmethod
    def _save_resolutions(thread_id, resolutions):
        """Write each side's resolution (or None to reopen) onto the root tile,
        skipping sides already open.

        Saves the tile directly: saving the tree runs attachments through the
        file-list datatype, which deletes their stored files."""
        tile = Tile.objects.get(
            resourceinstance_id=thread_id, nodegroup_id=G.nodegroup(A.MESSAGE_AUTHOR)
        )
        aliases = [
            alias for side in resolutions for alias in G.RESOLUTION_ALIASES[side]
        ]
        nodes = {
            alias: str(pk)
            for alias, pk in nodes_for(G.SLUG, aliases).values_list("alias", "pk")
        }
        changed = False
        for side, resolution in resolutions.items():
            date_node, by_node = (nodes[alias] for alias in G.RESOLUTION_ALIASES[side])
            if not resolution and not tile.data.get(date_node):
                continue
            resolved_date, resolved_by = resolution or (None, None)
            tile.data[date_node] = resolved_date
            tile.data[by_node] = (
                [{RESOURCE_ID: str(resolved_by)}] if resolved_by else None
            )
            changed = True
        if changed:
            tile.save()
