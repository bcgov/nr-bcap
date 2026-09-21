"""Compatibility entry point for the message and thread services.

New callers can use either service directly. This class preserves the combined
API used by existing views and dashboards; behavior lives in the two services.
"""

from bcap.services.message.message_service import (
    MessageService,
    NoAuthorContributor,
)
from bcap.services.message.thread_service import ModuleUnresolved, ThreadService

__all__ = ["BcapMessageService", "ModuleUnresolved", "NoAuthorContributor"]


class BcapMessageService(MessageService, ThreadService):
    """Expose message and thread operations through the existing service API."""
