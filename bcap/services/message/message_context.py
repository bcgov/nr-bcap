"""Shared message graph lookups and request-scoped viewer context."""

from functools import cache

from arches.app.models.models import TileModel
from arches.app.models.tile import Tile

from bcap.permissions.groups import is_internal_user
from bcap.services.contributor.organization_service import OrganizationService
from bcap.util.aliases.bcap_message import BcapMessageAliases as A
from bcap.util.graph import node_id, nodegroup_id
from bcap.util.tiles import references_any, resource_instance_id

AUTHOR, RECIPIENT = "author", "recipient"


class MessageGraph:
    """Node ids and raw tile reads on the message graph."""

    SLUG = "bcap_message"
    RESOLUTION_ALIASES = {
        AUTHOR: (A.AUTHOR_RESOLVED_DATE, A.AUTHOR_RESOLVED_BY),
        RECIPIENT: (A.RECIPIENT_RESOLVED_DATE, A.RECIPIENT_RESOLVED_BY),
    }

    @classmethod
    def node(cls, alias):
        return node_id(cls.SLUG, alias)

    @classmethod
    def nodegroup(cls, alias):
        return nodegroup_id(cls.SLUG, alias)

    @classmethod
    def content(cls, resource_id):
        """A message's main (message_content) tile data, or {}."""
        return (
            TileModel.objects.filter(
                nodegroup_id=cls.nodegroup(A.MESSAGE_AUTHOR),
                resourceinstance_id=resource_id,
            )
            .values_list("data", flat=True)
            .first()
        ) or {}

    @classmethod
    def thread_id(cls, message_id):
        """The thread-root resource id for a message (itself if it starts one)."""
        link = (
            TileModel.objects.filter(
                nodegroup_id=cls.nodegroup(A.RELATED_SOURCE_MESSAGE),
                resourceinstance_id=message_id,
            )
            .values_list(f"data__{cls.node(A.RELATED_SOURCE_MESSAGE)}", flat=True)
            .first()
        )
        return resource_instance_id(link) or str(message_id)

    @classmethod
    def archive_tiles(cls, contributor_id, thread_id=None):
        """The archived_by tiles naming this contributor, optionally for one
        thread."""
        tiles = Tile.objects.filter(
            references_any(cls.node(A.ARCHIVED_BY), [contributor_id]),
            nodegroup_id=cls.nodegroup(A.ARCHIVED_BY),
        )
        if thread_id is not None:
            tiles = tiles.filter(resourceinstance_id=str(thread_id))
        return tiles

    @classmethod
    def context_id(cls, message_id):
        """Read the saved context for the edit gate; PATCH bodies omit it."""
        content = cls.content(str(message_id))
        return resource_instance_id(content.get(cls.node(A.RESOURCE_CONTEXT)))


class MessageViewer:
    """Request-scoped viewer details, reused across threads."""

    def __init__(self, user):
        self.user = user
        self.staff = is_internal_user(user)
        contributors = OrganizationService()
        self.contributor_id = contributors.username_contributor_id(user.username)
        # Contributor ids the user acts as: self, current organizations, and (for
        # staff only) the Branch. Membership alone never grants staff access.
        parties = {*contributors.organization_ids(user.username), self.contributor_id}
        branch = contributors.archaeology_branch_id()
        if self.staff:
            parties.add(branch)
        else:
            parties.discard(branch)
        self.parties = {str(i) for i in parties - {None}}
        # Whether a Contributor is staff (or the Branch), looked up once per id.
        # Lives with this viewer (one request), so group changes show next request.
        self.is_staff_party = cache(contributors.contributor_is_internal)

    def side_of(self, author, recipient):
        """The viewer's side of a thread from its root's author and recipient:
        AUTHOR, RECIPIENT, or None when on neither.

        When exactly one of the two is staff, all staff are that side and anyone
        else who can see the thread is the other. Otherwise (an internal thread)
        it goes by the viewer's own parties, their groups included, and the
        author side wins a tie, so staff writing to the Branch stay its author."""
        author = str(author) if author else None
        recipient = str(recipient) if recipient else None
        author_staff = bool(author) and self.is_staff_party(author)
        recipient_staff = bool(recipient) and self.is_staff_party(recipient)
        if author_staff != recipient_staff:
            return AUTHOR if author_staff == self.staff else RECIPIENT
        if author in self.parties:
            return AUTHOR
        if recipient in self.parties:
            return RECIPIENT
        return None
