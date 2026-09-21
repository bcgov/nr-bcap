"""Shared message builders and stored-resolution assertions."""

from arches.app.models.models import TileModel
from bcap.services.message.message_context import MessageGraph
from bcap.util.aliases.bcap_message import BcapMessageAliases as A
from bcap.util.controlled_list import reference_value
from bcap.util.graph import node_info
from tests.services.contributor_fixtures import make_contributor


def _datetime(day):
    """Widen a bare day to noon UTC, since the message date nodes are
    datetime-with-timezone. Noon (not midnight) keeps .date() on the given day
    once the value is localized to the settings zone, whose offset would roll a
    midnight-UTC value back a day."""
    if day is None:
        return None
    return f"{day} 12:00:00+00:00"


def make_message(
    builder,
    *,
    context,
    author=None,
    recipient=None,
    is_internal=False,
    subject="",
    resolved_date=None,
    created=None,
    root=None,
):
    """A bcap_message on a parent resource, optionally a reply within a thread.
    A resolved_date resolves it for both sides."""
    message = builder.new_resource("bcap_message")
    builder.append_blank_tile_for_group(
        message,
        A.MESSAGE_CONTENT,  # the main nodegroup is named after its content node
        {
            A.MESSAGE_SUBJECT: builder.localized(subject),
            A.MESSAGE_CONTENT: builder.localized(subject),
            A.MESSAGE_TYPE: reference_value("bcap_message", A.MESSAGE_TYPE),
            A.MESSAGE_AUTHOR: author or make_contributor(builder, "Author", "Anon"),
            A.RECIPIENT: recipient,
            A.RESOURCE_CONTEXT: context,
            A.IS_INTERNAL: is_internal,
            A.AUTHOR_RESOLVED_DATE: _datetime(resolved_date),
            A.RECIPIENT_RESOLVED_DATE: _datetime(resolved_date),
            A.MESSAGE_CREATION_DATE: _datetime(created),
        },
    )
    if root is not None:
        builder.append_blank_tile_for_group(
            message, A.RELATED_SOURCE_MESSAGE, {A.RELATED_SOURCE_MESSAGE: root}
        )
    message.save(**builder.save_kwargs)
    builder.claim(message)
    return message


def resolution(message, side):
    """One side's stored (resolved date, resolved-by id), straight off the tile."""
    date_alias, by_alias = MessageGraph.RESOLUTION_ALIASES[side]
    date_node, nodegroup_id = node_info("bcap_message", date_alias)
    by_node, _ = node_info("bcap_message", by_alias)
    data = TileModel.objects.get(
        resourceinstance_id=message.pk, nodegroup_id=nodegroup_id
    ).data
    by = data.get(by_node)
    return data.get(date_node), (by[0]["resourceId"] if by else None)
