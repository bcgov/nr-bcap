"""Serializers for the BCAP message routes. Thin serializers so drf-spectacular
documents the bodies and the frontend's generated types follow."""

from dataclasses import dataclass

from rest_framework import serializers

from rest_framework_dataclasses.serializers import DataclassSerializer

from bcap.services.message.bcap_message_service import ModuleUnresolved
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


class BcapMessagePatchSerializer(serializers.Serializer):
    """PATCH body schema: commands on the message's thread rather than node
    edits, since both land on the thread root, not on the message."""

    archived = serializers.BooleanField(
        required=False,
        help_text="Toggle the caller's personal archive of the thread.",
    )
    resolved = serializers.BooleanField(
        required=False,
        help_text="Resolve or reopen the thread for everyone party to it.",
    )


class ThreadRootSerializer(BcapMessageSerializer):
    """A thread root plus the thread's latest activity, so the list renders
    without fetching each thread's messages."""

    last_message_date = serializers.DateTimeField(read_only=True)


class ModuleUnresolvedSerializer(DataclassSerializer):
    class Meta:
        dataclass = ModuleUnresolved
