from django.apps import AppConfig

from bcap.util.serializer_fields import register_offset_preserving_date_field


class BcapConfig(AppConfig):
    name = "bcap"
    is_arches_application = True

    def ready(self):
        # Temporary needs to be fixed in arches-queryset up stream
        register_offset_preserving_date_field()
