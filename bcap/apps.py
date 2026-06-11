from django.apps import AppConfig


class BcapConfig(AppConfig):
    name = "bcap"
    is_arches_application = True

    def ready(self):
        # Override the shared self-register defaults (for now): new external
        # users should land as Guest + Submitter, not public Resource Exporter.
        # _self_register reads this module global at call time.
        # Fix this in bcgov arches in subsequent commit
        from bcap.permissions.groups import Groups
        from bcgov_arches_common.util.auth import oauth_session_control

        oauth_session_control.DEFAULT_GROUPS = [
            Groups.GUEST,
            Groups.SUBMITTER,
        ]
