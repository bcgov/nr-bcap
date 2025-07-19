from bcgov_arches_common.management.commands.bc_reindex_database import (
    Command as BaseCommand,
)


class Command(BaseCommand):

    def get_index_order(self):
        return [
            "contributor",
            "government_person",
            "government",
            "legislative_act",
            "repository",
            "hca_permit",
            "archaeological_site",
            "site_visit",
            "archaeological_site_submission",
            "hria_discontinued_data",
            "sandcastle"
        ]
