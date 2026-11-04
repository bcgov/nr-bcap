import logging

from django.apps import AppConfig
from django.conf import settings

from bcap.util.serializer_fields import register_offset_preserving_date_field

logger = logging.getLogger(__name__)


class BcapConfig(AppConfig):
    name = "bcap"
    is_arches_application = True

    def ready(self):
        # Temporary needs to be fixed in arches-queryset up stream
        register_offset_preserving_date_field()
        if settings.CLAMAV_ENABLED:
            logger.info(
                "ClamAV virus scanning enabled (%s:%s)",
                settings.CLAMAV_HOST,
                settings.CLAMAV_PORT,
            )
        else:
            logger.warning("ClamAV virus scanning disabled: CLAMAV_ENABLED is not set")
