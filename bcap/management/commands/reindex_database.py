from django.core.management.base import BaseCommand

from arches.app.models import models
from arches.app.models.system_settings import settings
from arches.app.utils.index_database import index_concepts, index_resources_by_type


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-q',
            '--quiet',
            action='store_true',
            dest='quiet',
            default=False,
            help='It silences the status bar output during certain operations, use in celery operations for example',
        )

        parser.add_argument(
            '-b',
            '--batch_size',
            action='store',
            dest='batch_size',
            type=int,
            default=settings.BULK_IMPORT_BATCH_SIZE,
            help='The number of records to index as a group, the larger the number the more memory required',
        )

        parser.add_argument(
            '-mp',
            '--use_multiprocessing',
            action='store_true',
            dest='use_multiprocessing',
            default=False,
            help='It indexes the batches in parallel processes',
        )

        parser.add_argument(
            '-mxp',
            '--max_subprocesses',
            action='store',
            type=int,
            dest='max_subprocesses',
            default=0,
            help='It changes the process pool size when using use_multiprocessing. The default is ceil(cpu_count() / 2)',
        )

        parser.add_argument(
            '-rd',
            '--recalculate-descriptors',
            action='store_true',
            dest='recalculate_descriptors',
            default=True,
            help='It forces the primary descriptors to be recalculated before (re)indexing',
        )

    def get_index_order(self):
        return [
            'government',
            'government_person',
            'contributor',
            'repository',
            'legislative_act',
            'hca_permit',
            'archaeological_site',
            'archaeological_site_submission',
            'site_visit',
            'hria_discontinued_data',
            'sandcastle'
        ]

    def handle(self, *args, **options):
        self.reindex_database(
            clear_index=True,
            batch_size=options['batch_size'],
            quiet=options['quiet'],
            use_multiprocessing=options['use_multiprocessing'],
            max_subprocesses=options['max_subprocesses'],
            recalculate_descriptors=options['recalculate_descriptors'],
        )

    def reindex_database(
        self,
        clear_index=True,
        batch_size=settings.BULK_IMPORT_BATCH_SIZE,
        quiet=False,
        use_multiprocessing=False,
        max_subprocesses=0,
        recalculate_descriptors=True,
    ):
        resource_types = (
            models.GraphModel.objects.filter(isresource=True)
            .exclude(graphid=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
            .exclude(publication=None)
            .values_list('slug', 'graphid')
        )

        resource_types_lookup = {}

        for rt in resource_types:
            resource_types_lookup[rt[0]] = rt

        index_order = self.get_index_order()

        ordered_resource_types = []

        for i in index_order:
            if i in resource_types_lookup:
                ordered_resource_types.append(resource_types_lookup[i][1])
                print(f'Adding {i} to index queue')
            else:
                print(f'Skipping {i} - resource type not found')

        for key, value in resource_types_lookup.items():
            if key not in index_order:
                ordered_resource_types.append(value[1])
                print(f'Adding {key} to index queue (not in predefined order)')

        index_concepts(clear_index=clear_index, batch_size=batch_size)

        for i, resource_type_uuid in enumerate(ordered_resource_types):
            index_resources_by_type(
                [resource_type_uuid],
                clear_index=(clear_index and i == 0),
                batch_size=batch_size,
                quiet=quiet,
                use_multiprocessing=use_multiprocessing,
                max_subprocesses=max_subprocesses,
                recalculate_descriptors=recalculate_descriptors,
            )
