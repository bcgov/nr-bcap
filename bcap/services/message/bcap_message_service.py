"""Messages on a parent resource: per-recipient unread state and threading."""

import logging
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db.models import (
    BooleanField,
    Case,
    Count,
    DateTimeField,
    IntegerField,
    Q,
    Value,
    When,
)

from arches.app.models.models import TileModel
from arches.app.models.tile import Tile
from arches_querysets.models import ResourceTileTree

from bcap.util.graph import node_info
from bcap.util.bcap_aliases import RESOURCE_ID
from bcap.services.dashboard.base_graph_service import BaseGraphService
from bcap.services.contributor.contributor_service import ContributorService
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.util.aliases.bcap_message import BcapMessageAliases
from bcap.util.auth.groups import is_internal_user
from bcap.util.dates import parse_iso_or_set_value
from bcap.util.tiles import group_data, resource_instance_id

logger = logging.getLogger(__name__)

MESSAGE_GRAPH_SLUG = "bcap_message"


@dataclass
class ModuleUnread:
    """A process_module's unread message count for the viewer."""

    module_id: str
    unread_count: int


class NoAuthorContributor(Exception):
    """The posting user has no Contributor to author the message."""


class InternalMessageToExternal(Exception):
    """An internal-only message was addressed to an external recipient."""


class BcapMessageService(BaseGraphService):
    """Resolve, filter, and thread messages by their parent resource."""

    A = BcapMessageAliases

    @staticmethod
    def _contributor_id(username):
        """The user's Contributor id, or None."""
        return ContributorService().username_contributor_id(username)

    @staticmethod
    def _user_log_id(username):
        """A user's id for log lines, so a username (a credential) stays out of logs."""
        return (
            get_user_model()
            .objects.filter(username=username)
            .values_list("id", flat=True)
            .first()
        )

    @classmethod
    def resource_context_id(cls, data):
        """The resource id a new message's resource_context points at, or None."""
        return cls._payload_relation_id(data, cls.A.RESOURCE_CONTEXT)

    @classmethod
    def message_resource_context_id(cls, message_id):
        """The resource id a stored message's resource_context points at, or None.

        A PATCH strips resource_context from the body, so the edit gate reads the
        target from the saved message rather than the request."""
        context_id = (
            ResourceTileTree.get_tiles(
                MESSAGE_GRAPH_SLUG,
                nodes=cls.nodes(MESSAGE_GRAPH_SLUG, [cls.A.RESOURCE_CONTEXT]),
                resource_ids=[str(message_id)],
            )
            .values_list("resource_context__id", flat=True)
            .first()
        )
        return str(context_id) if context_id else None

    def set_read_state(self, request, message_id, data):
        """Set (a datetime) or clear (None) a message's read date from a PATCH
        body. Takes the request so the edit log records who saved."""
        if not self._payload_has(data, self.A.MESSAGE_READ_DATE):
            return None
        read_date = self._payload_node_value(data, self.A.MESSAGE_READ_DATE)
        message = ResourceTileTree.get_tiles(
            MESSAGE_GRAPH_SLUG, resource_ids=[str(message_id)]
        ).get()
        content = message.aliased_data.message_content.aliased_data
        content.message_read_date = parse_iso_or_set_value(read_date)
        message.save(request=request, partial=True)
        return message

    def set_archived_state(self, message_id, data, username):
        """Archive a thread for one viewer from a PATCH body's top-level archived flag.

        Three states: true archives, false unarchives, absent is a no-op. Personal
        and root-scoped: an archived_by tile on the thread root names each
        contributor who archived it, so one party never hides it from another and
        archiving from a reply lands on the root. No-op too without a Contributor."""
        if "archived" not in data:
            return
        contributor_id = self._contributor_id(username)
        if not contributor_id:
            logger.warning(
                "No Contributor for user %s; archive ignored.",
                self._user_log_id(username),
            )
            return
        thread_id = self._thread_id(message_id)
        existing = self._archived_by_tiles(contributor_id, thread_id)
        if not data["archived"]:
            self._delete_tiles(existing)
            return
        if not existing.exists():
            node_id, nodegroup_id = node_info(MESSAGE_GRAPH_SLUG, self.A.ARCHIVED_BY)
            Tile(
                resourceinstance_id=thread_id,
                nodegroup_id=nodegroup_id,
                data={node_id: [{RESOURCE_ID: str(contributor_id)}]},
            ).save()

    def unarchive_thread_for_all(self, message_id):
        """Clear every viewer's archive of a message's thread so a new reply
        resurfaces it for all. A new root has no such tiles, so it no-ops."""
        thread_id = self._thread_id(message_id)
        _, nodegroup_id = node_info(MESSAGE_GRAPH_SLUG, self.A.ARCHIVED_BY)
        self._delete_tiles(
            Tile.objects.filter(
                nodegroup_id=nodegroup_id,
                resourceinstance_id=str(thread_id),
            )
        )

    @staticmethod
    def _delete_tiles(tiles):
        """Delete one at a time through the proxy, so each deindexes and lands in
        the edit log. A queryset delete would do neither."""
        for tile in tiles:
            tile.delete()

    def _archived_by_tiles(self, contributor_id, thread_id=None):
        """archived_by tiles naming this contributor, optionally scoped to one root."""
        node_id, nodegroup_id = node_info(MESSAGE_GRAPH_SLUG, self.A.ARCHIVED_BY)
        tiles = Tile.objects.filter(
            nodegroup_id=nodegroup_id,
            **{f"data__{node_id}__contains": [{RESOURCE_ID: str(contributor_id)}]},
        )
        if thread_id is not None:
            tiles = tiles.filter(resourceinstance_id=str(thread_id))
        return tiles

    def _thread_id(self, message_id):
        """The thread-root resource id for a message (itself if it starts the thread)."""
        root_id = (
            ResourceTileTree.get_tiles(
                MESSAGE_GRAPH_SLUG,
                nodes=self.nodes(MESSAGE_GRAPH_SLUG, [self.A.RELATED_SOURCE_MESSAGE]),
                resource_ids=[str(message_id)],
            )
            .values_list("related_source_message__id", flat=True)
            .first()
        )
        return str(root_id) if root_id else str(message_id)

    @classmethod
    def _payload_node_value(cls, data, alias):
        """The node_value under an alias in the payload's message_content group."""
        return cls._group_node_value(data, cls.A.MESSAGE_CONTENT, alias)

    @classmethod
    def _payload_has(cls, data, alias):
        """Whether the payload carries this node at all (present but null still counts)."""
        return alias in cls._group_aliased_data(data, cls.A.MESSAGE_CONTENT)

    @classmethod
    def _payload_relation_id(cls, data, alias, group=None):
        """Resource id under a payload resource node, or None. Reads the
        message_content group unless another is named."""
        node_value = cls._group_node_value(data, group or cls.A.MESSAGE_CONTENT, alias)
        if isinstance(node_value, list):
            node_value = node_value[0] if node_value else {}
        return (node_value or {}).get(RESOURCE_ID)

    @classmethod
    def _is_internal_payload(cls, data):
        """The is_internal flag on the create payload (default False)."""
        return bool(cls._payload_node_value(data, cls.A.IS_INTERNAL))

    def prepare_message(self, data, user):
        """Fill in the author and enforce internal-message rules on a create payload."""
        author_id = self.set_author(data, user.username)
        if not is_internal_user(user):
            self._set_node(data, self.A.IS_INTERNAL, False)
        self.set_reply_recipient(data, author_id)
        self.validate_internal_recipient(data)

    @classmethod
    def set_author(cls, data, username):
        """Stamp the poster's Contributor as the author; raise if the user has none."""
        contributor_id = ContributorService().username_contributor_id(username)
        if not contributor_id:
            raise NoAuthorContributor(username)
        cls._set_node(data, cls.A.MESSAGE_AUTHOR, [{RESOURCE_ID: contributor_id}])
        return contributor_id

    @classmethod
    def set_reply_recipient(cls, data, author_id):
        """Address a reply from its thread rather than the payload, so a third party
        joining a thread writes to the root's other party instead of whichever
        contributor the client happened to have selected."""
        thread_id = cls._payload_relation_id(
            data, cls.A.RELATED_SOURCE_MESSAGE, cls.A.RELATED_SOURCE_MESSAGE
        )
        if not thread_id:
            return
        author_node, nodegroup_id = node_info(MESSAGE_GRAPH_SLUG, cls.A.MESSAGE_AUTHOR)
        recipient_node, _ = node_info(MESSAGE_GRAPH_SLUG, cls.A.RECIPIENT)
        root = (
            TileModel.objects.filter(
                nodegroup_id=nodegroup_id, resourceinstance_id=thread_id
            )
            .values_list("data", flat=True)
            .first()
        )
        if not root:
            return
        root_author = resource_instance_id(root.get(author_node))
        recipient = (
            resource_instance_id(root.get(recipient_node))
            if root_author == str(author_id)
            else root_author
        )
        if recipient:
            cls._set_node(data, cls.A.RECIPIENT, [{RESOURCE_ID: recipient}])

    @classmethod
    def _set_node(cls, data, alias, node_value):
        """Set a node's value in the payload's message_content group, creating the path."""
        group_data(data, cls.A.MESSAGE_CONTENT)[alias] = {"node_value": node_value}

    def validate_internal_recipient(self, data):
        """Refuse an internal-only message whose recipient is not staff."""
        if not self._is_internal_payload(data):
            return
        recipient_id = self._payload_relation_id(data, self.A.RECIPIENT)
        if recipient_id and not ContributorService().contributor_is_internal(
            recipient_id
        ):
            raise InternalMessageToExternal(recipient_id)

    def root_queryset(self, resource_id, user, archived=False):
        """The thread-starting messages on a parent resource, gated for externals.
        Archive is per-user: a thread is archived only for the contributors on its root's
        archived_by."""
        roots = (
            ResourceTileTree.get_tiles(
                MESSAGE_GRAPH_SLUG, as_representation=True
            ).filter(
                resource_context__id=str(resource_id),
                related_source_message__isnull=True,
            )
            # Newest thread first; createdtime breaks ties on a null creation date.
            .order_by("-message_creation_date", "-createdtime")
        )
        roots = self._by_archived(roots, user.username, archived)
        # Coarse role gate for now; a future groups ticket moves this to Guardian.
        if not is_internal_user(user):
            roots = self._external_visible(roots, user.username)
        unread, latest = self._thread_summaries(resource_id, user.username)
        # A subquery annotation can't reach these: the thread link is a JSON node,
        # not a column an OuterRef can compare against, so map them on by pk.
        return roots.annotate(
            unread_count=Case(
                *[When(pk=r, then=Value(n)) for r, n in unread.items()],
                default=Value(0),
                output_field=IntegerField(),
            ),
            last_message_date=Case(
                *[When(pk=r, then=Value(dt)) for r, dt in latest.items()],
                default=None,
                output_field=DateTimeField(),
            ),
        )

    def _thread_summaries(self, resource_id, username):
        """Per thread on a resource, in one query: the viewer's unread count and
        the latest message date. A message's thread is the message it replies to,
        or itself if it is a root; replies share the resource_context, so one
        filter covers the whole thread."""
        contributor_id = self._contributor_id(username)
        rows = (
            ResourceTileTree.get_tiles(
                MESSAGE_GRAPH_SLUG,
                nodes=self.nodes(
                    MESSAGE_GRAPH_SLUG,
                    [
                        self.A.RECIPIENT,
                        self.A.MESSAGE_READ_DATE,
                        self.A.MESSAGE_CREATION_DATE,
                        self.A.RESOURCE_CONTEXT,
                        self.A.RELATED_SOURCE_MESSAGE,
                    ],
                ),
            )
            .filter(resource_context__id=str(resource_id))
            .values(
                "pk",
                "related_source_message__id",
                "recipient__id",
                "message_read_date",
                "message_creation_date",
            )
        )
        unread, latest = {}, {}
        for row in rows:
            root_id = str(row["related_source_message__id"] or row["pk"])
            date = row["message_creation_date"]
            if date and (root_id not in latest or date > latest[root_id]):
                latest[root_id] = date
            if (
                contributor_id
                and str(row["recipient__id"]) == str(contributor_id)
                and row["message_read_date"] is None
            ):
                unread[root_id] = unread.get(root_id, 0) + 1
        return unread, latest

    def _by_archived(self, roots, username, archived):
        """Narrow roots to the viewer's archived or active threads."""
        contributor_id = self._contributor_id(username)
        if not contributor_id:
            return roots.none() if archived else roots
        archived_ids = self._archived_by_tiles(contributor_id).values_list(
            "resourceinstance_id", flat=True
        )
        if archived:
            return roots.filter(pk__in=archived_ids)
        return roots.exclude(pk__in=archived_ids)

    def thread_queryset(self, thread_id, user):
        """One thread's messages, oldest first, gated for external users. Each row
        is annotated is_unread for this viewer: addressed to them and not yet read,
        so a message they authored is never unread to them."""
        contributor_id = self._contributor_id(user.username)
        if contributor_id:
            unread = Case(
                When(
                    recipient__id=contributor_id,
                    message_read_date__isnull=True,
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            )
        else:
            unread = Value(False, output_field=BooleanField())
        messages = (
            ResourceTileTree.get_tiles(
                MESSAGE_GRAPH_SLUG,
                as_representation=True,
            )
            .filter(Q(pk=str(thread_id)) | Q(related_source_message__id=str(thread_id)))
            .annotate(is_unread=unread)
            # Oldest first; createdtime breaks ties on a null creation date.
            .order_by("message_creation_date", "createdtime")
        )
        if not is_internal_user(user):
            messages = self._external_visible(messages, user.username)
        return messages

    def unread_by_module(self, submission_id, username) -> list[ModuleUnread]:
        """The viewer's unread count per process_module of a submission, one entry
        per module tile."""
        contexts = ProcessRequirementService().module_message_contexts(
            str(submission_id)
        )
        counts = self.unread_counts_by_context(contexts.values(), username)
        return [
            ModuleUnread(module_id=tile, unread_count=counts.get(ctx, 0))
            for tile, ctx in contexts.items()
        ]

    def attachments_file_key(self):
        """The multipart field key the create endpoint expects for attachment
        files: file-list_<attachments node id>, resolved from the graph so no
        node id is hard-coded on the client."""
        node_id, _ = node_info(MESSAGE_GRAPH_SLUG, self.A.ATTACHMENTS)
        return f"file-list_{node_id}"

    def unread_count_across(self, context_ids, username):
        """Unread messages for the user across the given contexts, as one count."""
        return sum(self.unread_counts_by_context(context_ids, username).values())

    def unread_counts_by_context(self, context_ids, username):
        """Unread messages for the user per resource context, in one grouped query."""
        contributor_id = self._contributor_id(username)
        if not contributor_id:
            logger.warning(
                "No Contributor for user %s; unread counts are 0.",
                self._user_log_id(username),
            )
            return {}
        if not context_ids:
            return {}
        rows = (
            ResourceTileTree.get_tiles(
                MESSAGE_GRAPH_SLUG,
                # Annotate only the nodes filtered on, not the whole message
                # graph, so the count query stays cheap.
                nodes=self.nodes(
                    MESSAGE_GRAPH_SLUG,
                    [
                        self.A.RECIPIENT,
                        self.A.MESSAGE_READ_DATE,
                        self.A.RESOURCE_CONTEXT,
                    ],
                ),
            )
            .filter(
                recipient__id=contributor_id,
                message_read_date__isnull=True,
                resource_context__id__in=[str(cid) for cid in context_ids],
            )
            .values("resource_context__id")
            .annotate(unread=Count("pk"))
        )
        return {str(row["resource_context__id"]): row["unread"] for row in rows}

    def _external_visible(self, messages, username):
        """What an external user may see: messages they're party to, never internal-only."""
        return self.recipient_or_author(messages, username).exclude(is_internal=True)

    def recipient_or_author(self, messages, username):
        """Narrow to messages the user's Contributor is party to (recipient or author)."""
        contributor_id = self._contributor_id(username)
        if not contributor_id:
            logger.warning(
                "No Contributor for user %s; no messages visible.",
                self._user_log_id(username),
            )
            return messages.none()
        return messages.filter(
            Q(recipient__id=contributor_id) | Q(message_author__id=contributor_id)
        )
