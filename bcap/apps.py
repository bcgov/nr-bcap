from django.apps import AppConfig


class BcapConfig(AppConfig):
    name = "bcap"
    is_arches_application = True

    def ready(self):
        # Install the OpenAPI date-node override at startup. The documented views
        # don't import bcap.schema, so this is what guarantees the override is in
        # place before drf-spectacular generates the schema.
        from bcap import schema  # noqa: F401
