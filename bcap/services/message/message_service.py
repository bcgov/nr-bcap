"""Single-message reads, recipient options and create-payload preparation."""

from rest_framework.exceptions import PermissionDenied

from bcap.permissions.groups import is_internal_user
from bcap.permissions.permit_access import PermitAccess
from bcap.services.contributor.contributor_service import ContributorService
from bcap.services.message.message_context import (
    AUTHOR,
    RECIPIENT,
    MessageGraph as G,
    MessageViewer,
)
from bcap.services.message.thread_service import ThreadService
from bcap.util.aliases.bcap_message import BcapMessageAliases as A
from bcap.util.tiles import (
    payload_resource_id,
    resource_instance_value,
    set_payload_node,
)


class NoAuthorContributor(Exception):
    """The posting user has no Contributor to author the message."""


class MessageService:
    """Read single messages and ready new ones, using the thread service's
    visibility rules."""

    @classmethod
    def detail_query(cls, message_id, user):
        """One visible message, gated on its parent resource first so a denied
        read returns 403 rather than an empty result."""
        PermitAccess.require_view(user, G.context_id(message_id))
        return ThreadService.base_query(
            MessageViewer(user), resource_ids=[str(message_id)]
        )

    def recipient_options(self, resource_id, user):
        """Contributors the user may address on a readable resource. Staff also
        get the proponent."""
        PermitAccess.require_view(user, str(resource_id))
        return ContributorService().contributors_for_resource(
            str(resource_id), with_proponent=is_internal_user(user)
        )

    def prepare_create_payload(self, data, user):
        """Ready a POST body for saving: stamp the author, clear any client-sent
        resolutions, take the thread's fields for a reply or decide internal for
        a new thread, then require change access to the parent resource."""
        viewer = MessageViewer(user)
        self.stamp_author(data, viewer)
        for alias in (*G.RESOLUTION_ALIASES[AUTHOR], *G.RESOLUTION_ALIASES[RECIPIENT]):
            set_payload_node(data, A.MESSAGE_CONTENT, alias, None)
        if not self.inherit_thread_fields(data, viewer):
            set_payload_node(
                data,
                A.MESSAGE_CONTENT,
                A.IS_INTERNAL,
                self._is_new_internal_thread(data, viewer),
            )
        PermitAccess.require_change(
            user, payload_resource_id(data, A.MESSAGE_CONTENT, A.RESOURCE_CONTEXT)
        )

    @staticmethod
    def stamp_author(data, viewer: MessageViewer):
        """Write the poster's Contributor into the author node; raise
        NoAuthorContributor when they have none."""
        if not viewer.contributor_id:
            raise NoAuthorContributor(viewer.user.username)
        set_payload_node(
            data,
            A.MESSAGE_CONTENT,
            A.MESSAGE_AUTHOR,
            resource_instance_value(viewer.contributor_id),
        )

    @staticmethod
    def inherit_thread_fields(data, viewer: MessageViewer):
        """For a reply: require the thread be visible, point the link at its
        root, address the root's other side and copy the root's subject, type and
        internal flag. Returns False when the payload starts a new thread."""
        thread_id = payload_resource_id(
            data, A.RELATED_SOURCE_MESSAGE, A.RELATED_SOURCE_MESSAGE
        )
        if not thread_id:
            return False
        thread_id = G.thread_id(thread_id)
        if not ThreadService.base_query(
            viewer, resource_ids=[thread_id], aliases=[A.RESOURCE_CONTEXT]
        ).exists():
            raise PermissionDenied("You cannot reply to this thread.")
        set_payload_node(
            data,
            A.RELATED_SOURCE_MESSAGE,
            A.RELATED_SOURCE_MESSAGE,
            resource_instance_value(thread_id),
        )
        root = G.content(thread_id)

        # A reply goes to whichever side of the thread the poster isn't on.
        author, recipient = G.author_and_recipient(root)
        to = recipient if viewer.side_of(author, recipient) == AUTHOR else author
        if to:
            set_payload_node(
                data, A.MESSAGE_CONTENT, A.RECIPIENT, resource_instance_value(to)
            )
        set_payload_node(
            data,
            A.MESSAGE_CONTENT,
            A.IS_INTERNAL,
            bool(root.get(G.node(A.IS_INTERNAL))),
        )

        # Subject and type belong to the thread, so the root's win over the client's.
        for alias in (A.MESSAGE_TYPE, A.MESSAGE_SUBJECT):
            inherited = root.get(G.node(alias))
            if inherited:
                set_payload_node(data, A.MESSAGE_CONTENT, alias, inherited)
        return True

    @staticmethod
    def _is_new_internal_thread(data, viewer: MessageViewer):
        """Whether a new thread is internal: only staff writing to staff or the
        Branch."""
        recipient_id = payload_resource_id(data, A.MESSAGE_CONTENT, A.RECIPIENT)
        return bool(
            recipient_id and viewer.staff and viewer.is_staff_party(recipient_id)
        )
