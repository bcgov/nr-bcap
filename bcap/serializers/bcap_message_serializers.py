"""Serializers for the BCAP message routes. Thin serializers so drf-spectacular
documents the bodies and the frontend's generated types follow."""

from dataclasses import dataclass

from rest_framework import serializers

from rest_framework_dataclasses.serializers import DataclassSerializer

from bcap.services.message.bcap_message_service import ModuleUnread
from bcap.views.generated.bcap_message import BcapMessageSerializer


@dataclass
class ThreadsQuery:
    """Query params for the threads list."""

    archived: bool = False


class ThreadsQuerySerializer(DataclassSerializer):
    """Documents the params in the spec and coerces archived from the usual
    truthy strings (true/1) rather than a bare == "true"."""

    archived = serializers.BooleanField(
        default=False,
        help_text="Return the viewer's archived threads instead of active ones.",
    )

    class Meta:
        dataclass = ThreadsQuery


class BcapMessagePatchSerializer(BcapMessageSerializer):
    """PATCH body schema: the message representation plus a top-level archived
    flag that toggles the caller's personal archive of the whole thread. It is a
    command, not a stored node, so it lives beside aliased_data rather than in it."""

    archived = serializers.BooleanField(
        required=False,
        help_text="Toggle the caller's personal archive of the thread.",
    )


class ThreadRootSerializer(BcapMessageSerializer):
    """A thread root plus service-annotated summary fields, so the list renders
    unread state and last activity without fetching each thread's messages."""

    unread_count = serializers.IntegerField(read_only=True)
    last_message_date = serializers.DateTimeField(read_only=True)


class ThreadMessageSerializer(BcapMessageSerializer):
    """A thread message plus the queryset's per-viewer is_unread annotation, so
    the client shows unread only for messages addressed to the viewer."""

    is_unread = serializers.BooleanField(read_only=True)


class ModuleUnreadSerializer(DataclassSerializer):
    class Meta:
        dataclass = ModuleUnread
