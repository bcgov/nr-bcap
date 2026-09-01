"""Reset Guardian permissions to the BCAP default-deny baseline.

Clears every group and per-user nodegroup grant and re-asserts
INTERNAL_GRAPH_PERMISSION_DEFAULTS, then reindexes the affected resources.
Under default-deny, anonymous/Guest and any group not in the policy are denied
implicitly, so no per-instance no_access passes are needed; owner access stays
intact because it is implicit (resource.principaluser)."""

import logging

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from arches.app.models import models
from arches.app.models.system_settings import settings
from arches.app.utils.index_database import index_resources_by_type

from bcap.permissions.bcap_arches_permission_framework import (
    BcapArchesPermissionFramework,
)
from bcap.permissions.graph_policy import (
    INTERNAL_GRAPH_PERMISSION_DEFAULTS,
    MANAGED_GROUPS,
)

logger = logging.getLogger(__name__)


def parse_slugs(raw):
    """The requested slugs, or None for every policy graph."""
    if not raw:
        return None
    slugs = [slug.strip() for slug in raw.split(",")]
    if unknown := set(slugs) - set(INTERNAL_GRAPH_PERMISSION_DEFAULTS):
        raise CommandError("Slug(s) not in the policy: %s" % ", ".join(unknown))
    return slugs


def missing_groups():
    """Policy groups with no row in the DB, whose grants will be skipped."""
    return MANAGED_GROUPS - set(
        Group.objects.filter(name__in=MANAGED_GROUPS).values_list("name", flat=True)
    )


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-s",
            "--slugs",
            dest="slugs",
            default=None,
            help="Comma-separated graph slugs to reset (default: all policy graphs)",
        )
        parser.add_argument(
            "--skip-index",
            action="store_true",
            dest="skip_index",
            default=False,
            help="Apply permissions without reindexing",
        )

    def handle(self, *args, **options):
        slugs = parse_slugs(options["slugs"])

        if missing := missing_groups():
            logger.warning(
                "Groups missing from the DB, their grants were skipped: %s",
                ", ".join(sorted(missing)),
            )

        applied = BcapArchesPermissionFramework.apply_permission_defaults(slugs)
        logger.info("Reset permission defaults on %s graphs", len(applied))
        if options["skip_index"]:
            return

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
