from bcgov_arches_common.management.commands.bc_reindex_database import (
    Command as BaseCommand,
)


class Command(BaseCommand):

    def get_index_order(self):
        return [
            "contributor",
            "lg_person",
            "local_government",
            "legislative_act",
            "repository",
            "hca_permit",
            "archaeological_site",
            "site_visit",
            "hria_discontinued_data",
            "project_sandbox",
            "site_submission",
        ]
