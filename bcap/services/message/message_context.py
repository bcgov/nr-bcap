"""Shared message graph lookups and request-scoped viewer context."""

from dataclasses import dataclass

from arches.app.models.models import TileModel
from arches.app.models.tile import Tile

from bcap.permissions.groups import is_internal_user
from bcap.services.contributor.organization_service import OrganizationService
from bcap.util.aliases.bcap_message import BcapMessageAliases as A
from bcap.util.bcap_aliases import RESOURCE_ID
from bcap.util.graph import node_id, nodegroup_id
from bcap.util.tiles import references_any, resource_instance_id

AUTHOR, RECIPIENT = "author", "recipient"


@dataclass
class ThreadRoot:
    """Who takes part in a thread and where it stands, from its root."""

    author: str | None
    recipient: str | None
    participants: set[str]
    resolved: dict[str, bool]
    answered: bool


class MessageGraph:
    """Node ids and raw tile reads on the message graph."""

    SLUG = "bcap_message"
    RESOLUTION_ALIASES = {
        AUTHOR: (A.THREAD_AUTHOR_RESOLVED_DATE, A.THREAD_AUTHOR_RESOLVED_BY),
        RECIPIENT: (A.THREAD_RECIPIENT_RESOLVED_DATE, A.THREAD_RECIPIENT_RESOLVED_BY),
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
        return next((data for _, data in cls.contents([resource_id])), {})

    @classmethod
    def contents(cls, resource_ids):
        """(resource id, content tile data) for each of these messages."""
        return TileModel.objects.filter(
            nodegroup_id=cls.nodegroup(A.MESSAGE_CONTENT),
            resourceinstance_id__in=[str(r) for r in resource_ids],
        ).values_list("resourceinstance_id", "data")

    @classmethod
    def roots(cls, resource_ids):
        """{root id: ThreadRoot} for these thread roots."""
        nodes = cls._root_nodes()
        return {
            str(root_id): cls._read_root(data, nodes)
            for root_id, data in cls.contents(resource_ids)
        }

    @classmethod
    def root(cls, content):
        """A thread root's content tile data as a ThreadRoot."""
        return cls._read_root(content, cls._root_nodes())

    @classmethod
    def _root_nodes(cls):
        aliases = (
            A.MESSAGE_AUTHOR,
            A.RECIPIENT,
            A.THREAD_PARTICIPANTS,
            A.THREAD_ANSWERED,
            *(date for date, _ in cls.RESOLUTION_ALIASES.values()),
        )
        return {alias: cls.node(alias) for alias in aliases}

    @classmethod
    def _read_root(cls, content, nodes):
        author = resource_instance_id(content.get(nodes[A.MESSAGE_AUTHOR]))
        recipient = resource_instance_id(content.get(nodes[A.RECIPIENT]))
        stored = {
            ref[RESOURCE_ID] for ref in content.get(nodes[A.THREAD_PARTICIPANTS]) or []
        }
        return ThreadRoot(
            author=author,
            recipient=recipient,
            # Threads from before the list was kept fall back to both sides.
            participants=stored or set(filter(None, (author, recipient))),
            resolved={
                side: bool(content.get(nodes[date]))
                for side, (date, _) in cls.RESOLUTION_ALIASES.items()
            },
            answered=bool(content.get(nodes[A.THREAD_ANSWERED])),
        )

    @classmethod
    def thread_id(cls, message_id):
        """The thread-root resource id for a message (itself if it starts one)."""
        link = cls.content(message_id).get(cls.node(A.THREAD))
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
        self.staff_parties = {}

    def is_staff_party(self, contributor_id):
        """Whether a Contributor is staff (or the Branch), looked up once per id
        for this viewer."""
        if contributor_id not in self.staff_parties:
            self.staff_parties[contributor_id] = (
                OrganizationService().contributor_is_internal(contributor_id)
            )
        return self.staff_parties[contributor_id]

    @classmethod
    def for_user(cls, user):
        """The viewer for this user, built once and kept on the user object,
        which lives for one request. Arches pickles the user into its
        permission cache, so the viewer must stay picklable."""
        if not hasattr(user, "message_viewer"):
            user.message_viewer = cls(user)
        return user.message_viewer

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

    def participates(self, root: ThreadRoot):
        """Whether the viewer, or a group of theirs, takes part in the thread.
        Only participants are alerted."""
        return bool(root.participants & self.parties)

    def thread_side(self, root: ThreadRoot):
        """The viewer's side of the thread. A participant on neither side
        (someone who joined) is the recipient side, since their replies go to
        the author."""
        side = self.side_of(root.author, root.recipient)
        if side is None and self.participates(root):
            return RECIPIENT
        return side
