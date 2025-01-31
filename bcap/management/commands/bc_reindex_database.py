from bcgov_arches_common.management.commands.bc_reindex_database import (
    Command as BaseCommand,
)


class Command(BaseCommand):

    def get_index_order(self):
        return [
            "contributor",
            "local_government",
            "lg_person",
            "legislative_act",
            "archaeological_permit",
            "heritage_site",
            "arch_site_visit",
            "project_sandbox",
            "site_submission",
        ]
