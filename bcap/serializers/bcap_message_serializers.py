"""Serializers for the BCAP message routes. Thin serializers so drf-spectacular
documents the bodies and the frontend's generated types follow."""

from rest_framework import serializers

from rest_framework_dataclasses.serializers import DataclassSerializer

from bcap.services.message.thread_service import ModuleUnresolved, ThreadService
from bcap.views.generated.bcap_message import BcapMessageSerializer


class ThreadsQuerySerializer(serializers.Serializer):
    """Query params for the threads list."""

    resource_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=200,
        help_text="The resources to list threads for, as repeated params.",
    )
    archived = serializers.BooleanField(
        default=False,
        help_text="Return the viewer's archived threads instead of active ones.",
    )


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
    """A thread root plus where the viewer stands on it."""

    viewer_side = serializers.CharField(
        read_only=True,
        help_text="The viewer's side of the thread, author or recipient, whose "
        "resolved_* nodes are theirs; empty when they are on neither.",
    )
    viewer_needs_action = serializers.BooleanField(
        read_only=True,
        help_text="Whether the thread awaits the viewer: they (or a group of "
        "theirs) take part, their side is unresolved, and, if they started it, "
        "someone has replied.",
    )


class ThreadMessageSerializer(BcapMessageSerializer):
    """A thread message plus whether its author is staff, so the client can mark
    who spoke for the Archaeology Branch."""

    author_is_staff = serializers.SerializerMethodField()

    def get_author_is_staff(self, message) -> bool:
        return ThreadService.author_is_staff(message, self.context["request"].user)


class ModuleUnresolvedSerializer(DataclassSerializer):
    class Meta:
        dataclass = ModuleUnresolved
