from django.apps import AppConfig


class BcapConfig(AppConfig):
    name = "bcap"
    is_arches_application = True

    def ready(self):
        from bcap.datatypes.querysets_patch import temp_performance_fix_patch

        temp_performance_fix_patch()
