"""Messages on a parent resource: per-recipient unread state and threading."""

import logging

from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from arches_querysets.models import ResourceTileTree

from bcap.services.dashboard.base_graph_service import BaseGraphService
from bcap.services.contributor_service import ContributorService
from bcap.util.aliases.bcap_message import BcapMessageAliases
from bcap.util.auth.groups import is_internal_user
from bcap.util.dates import parse_iso_or_set_value

logger = logging.getLogger(__name__)

MESSAGE_GRAPH_SLUG = "bcap_message"


class NoAuthorContributor(Exception):
    """The posting user has no Contributor to author the message."""


class InternalMessageToExternal(Exception):
    """An internal-only message was addressed to an external recipient."""


class BcapMessageService(BaseGraphService):
    """Resolve, filter, and thread messages by their parent resource."""

    A = BcapMessageAliases

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

    def set_read_state(self, message_id, data):
        """Set (a datetime) or clear (None) a message's read date from a PATCH body."""
        read_date = self._payload_node_value(data, self.A.MESSAGE_READ_DATE)
        message = ResourceTileTree.get_tiles(
            MESSAGE_GRAPH_SLUG, resource_ids=[str(message_id)]
        ).get()
        content = message.aliased_data.message_content.aliased_data
        content.message_read_date = parse_iso_or_set_value(read_date)
        # Save as a reviewer (admin): provisional edit applies if not?
        message.save(request=None, force_admin=True, partial=True)
        return message

    @classmethod
    def _payload_node_value(cls, data, alias):
        """The node_value under an alias in the payload's message_content group."""
        return cls._group_node_value(data, cls.A.MESSAGE_CONTENT, alias)

    @classmethod
    def _payload_relation_id(cls, data, alias):
        """Resource id under the payload's message_content resource node, or None."""
        node_value = cls._payload_node_value(data, alias)
        if isinstance(node_value, list):
            node_value = node_value[0] if node_value else {}
        return (node_value or {}).get("resourceId")

    @classmethod
    def _is_internal_payload(cls, data):
        """The is_internal flag on the create payload (default False)."""
        return bool(cls._payload_node_value(data, cls.A.IS_INTERNAL))

    def prepare_message(self, data, user):
        """Fill in the author and enforce internal-message rules on a create payload."""
        self.set_author(data, user.username)
        if not is_internal_user(user):
            self._set_node(data, self.A.IS_INTERNAL, False)
        self.validate_internal_recipient(data)

    @classmethod
    def set_author(cls, data, username):
        """Stamp the poster's Contributor as the author; raise if the user has none."""
        contributor_id = ContributorService().username_contributor_id(username)
        if not contributor_id:
            raise NoAuthorContributor(username)
        cls._set_node(data, cls.A.MESSAGE_AUTHOR, [{"resourceId": contributor_id}])

    @classmethod
    def _set_node(cls, data, alias, node_value):
        """Set a node's value in the payload's message_content group, creating the path."""
        content = data.setdefault("aliased_data", {}).setdefault(
            cls.A.MESSAGE_CONTENT, {}
        )
        content.setdefault("aliased_data", {})[alias] = {"node_value": node_value}

    def validate_internal_recipient(self, data):
        """Refuse an internal-only message whose recipient is not staff."""
        if not self._is_internal_payload(data):
            return
        recipient_id = self._payload_relation_id(data, self.A.RECIPIENT)
        if recipient_id and not ContributorService().contributor_is_internal(
            recipient_id
        ):
            raise InternalMessageToExternal(recipient_id)

    def root_queryset(self, resource_id, user):
        """The thread-starting messages on a parent resource, gated for externals."""
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
        # Coarse role gate for now; a future groups ticket moves this to Guardian.
        if not is_internal_user(user):
            roots = self._external_visible(roots, user.username)
        return roots

    def thread_queryset(self, thread_id, user):
        """One thread's messages, oldest first, gated for external users."""
        messages = (
            ResourceTileTree.get_tiles(
                MESSAGE_GRAPH_SLUG, as_representation=True
            ).filter(
                Q(pk=str(thread_id)) | Q(related_source_message__id=str(thread_id))
            )
            # Oldest first; createdtime breaks ties on a null creation date.
            .order_by("message_creation_date", "createdtime")
        )
        if not is_internal_user(user):
            messages = self._external_visible(messages, user.username)
        return messages

    def unread_count_across(self, context_ids, username):
        """Unread messages for the user across the given contexts, as one count."""
        return sum(self.unread_counts_by_context(context_ids, username).values())

    def unread_counts_by_context(self, context_ids, username):
        """Unread messages for the user per resource context, in one grouped query."""
        contributor_id = ContributorService().username_contributor_id(username)
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
        contributor_id = ContributorService().username_contributor_id(username)
        if not contributor_id:
            logger.warning(
                "No Contributor for user %s; no messages visible.",
                self._user_log_id(username),
            )
            return messages.none()
        return messages.filter(
            Q(recipient__id=contributor_id) | Q(message_author__id=contributor_id)
        )
