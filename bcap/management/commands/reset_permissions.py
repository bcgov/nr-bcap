"""Reset Guardian permissions to the BCAP default-deny baseline.

Clears every group/anonymous nodegroup grant and re-asserts
INTERNAL_GRAPH_PERMISSION_DEFAULTS, then reindexes the affected resources.
Under default-deny, anonymous/Guest and any group not in the policy are denied
implicitly, so no per-instance no_access passes are needed; owner access stays
intact because it is implicit (resource.principaluser)."""

import logging

from django.core.management.base import BaseCommand

from arches.app.models import models
from arches.app.models.system_settings import settings
from arches.app.utils.index_database import index_resources_by_type

from bcap.permissions.bcap_arches_permission_framework import (
    BcapArchesPermissionFramework,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-s",
            "--slugs",
            dest="slugs",
            default=None,
            help="Comma-separated graph slugs to reset (default: all policy " "graphs)",
        )

    def handle(self, *args, **options):
        slugs = (
            [slug.strip() for slug in options["slugs"].split(",")]
            if options["slugs"]
            else None
        )
        graph_ids = None
        if slugs:
            graph_ids = [
                str(graph_id)
                for graph_id in models.GraphModel.objects.filter(
                    slug__in=slugs
                ).values_list("graphid", flat=True)
            ]

        applied = BcapArchesPermissionFramework.apply_permission_defaults(graph_ids)
        print("Reset permission defaults on %s graphs" % len(applied))

        resource_types_uuid = (
            models.GraphModel.objects.filter(graphid__in=applied)
            .exclude(publication=None)
            .values_list("graphid", flat=True)
        )
        index_resources_by_type(
            resource_types_uuid,
            clear_index=True,
            batch_size=settings.BULK_IMPORT_BATCH_SIZE,
            quiet=False,
            recalculate_descriptors=False,
        )
