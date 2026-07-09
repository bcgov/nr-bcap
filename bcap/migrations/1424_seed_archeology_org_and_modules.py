"""Seed the Archaeology Branch organization Contributor (linking its group's
members), then reseed the process-requirement templates. Reverse removes both."""

import logging

from django.contrib.auth.models import Group
from django.db import migrations

from arches.app.models.models import TileModel
from arches.app.models.resource import Resource
from arches.app.search.mappings import RESOURCES_INDEX
from arches.app.search.search_engine_factory import SearchEngineFactory
from arches_controlled_lists.models import List, ListItem, ListItemValue
from arches_querysets.models import ResourceTileTree

from bcap.builders.contributor_builder import ContributorBuilder, ContributorSpec
from bcap.builders.resource_builder import ResourceBuilder
from bcap.management.commands._dashboard_seed_base import _bulk_index
from bcap.services.dashboard.contributor_service import ContributorService
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.services.process_requirement.template_specs import (
    flatten,
    supported_permit_types,
)
from bcap.util.aliases.contributor import ContributorAliases as A
from bcap.util.auth.roles import Roles
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.controlled_list import reference_value
from bcap.util.dashboard.requirement_flow_seed import RequirementFlowBuilder
from bcap.util.graph import get_node
from bcap.util.indexing import bulk_index

logger = logging.getLogger(__name__)

ORG_NAME = Roles.ARCHAEOLOGY_BRANCH
GROUP_NAME = ORG_NAME

# The graph's contributor_type reference node points at this controlled list,
# but nothing creates it: its items live only in the old concept collection of
# the same id and were never converted to CLM rows. Seed the two canonical
# items (reusing the collection's ids) so reading a contributor_type value
# below, and on any fresh database, finds them.
CONTRIBUTOR_TYPE_LIST_ID = "6a2bcd73-f98f-5d3f-bec5-e2c9566d2d81"
CONTRIBUTOR_TYPES = [
    # (item id, prefLabel value id, label, sortorder, concept uri)
    (
        "8c4e2933-a97a-5f47-89e7-78d1d8aaad81",
        "c0b10d00-fbfa-58c3-ba46-3dc39d61a87e",
        "Individual",
        0,
        "http://bcap/bcap8c4e2933-a97a-5f47-89e7-78d1d8aaad81",
    ),
    (
        "fd2053d3-c010-519a-97e5-52f3c7b508e2",
        "891278e4-5d67-571a-a0c4-414896d36d1c",
        "Organization",
        1,
        "http://bcap/bcapfd2053d3-c010-519a-97e5-52f3c7b508e2",
    ),
]


def seed_contributor_type_list(apps, schema_editor):
    controlled_list, _ = List.objects.get_or_create(
        pk=CONTRIBUTOR_TYPE_LIST_ID,
        defaults={"name": "Contributor Type", "dynamic": False, "searchable": False},
    )
    for item_id, value_id, label, sortorder, uri in CONTRIBUTOR_TYPES:
        item, _ = ListItem.objects.get_or_create(
            pk=item_id,
            defaults={"list": controlled_list, "sortorder": sortorder, "uri": uri},
        )
        ListItemValue.objects.get_or_create(
            pk=value_id,
            defaults={
                "list_item": item,
                "valuetype_id": "prefLabel",
                "language_id": "en",
                "value": label,
            },
        )


def _name_node():
    return str(get_node(GraphSlugs.CONTRIBUTOR, A.CONTRIBUTOR_NAME).pk)


def _org_ids():
    return list(
        TileModel.objects.filter(
            **{f"data__{_name_node()}__en__value": ORG_NAME}
        ).values_list("resourceinstance_id", flat=True)
    )


def _link_member(contributor_id, org):
    contributor = ResourceTileTree.get_tiles(GraphSlugs.CONTRIBUTOR).get(
        pk=contributor_id
    )
    group_tile = contributor.aliased_data.contributor
    if group_tile is None:
        logger.warning("Contributor %s has no group tile; not linked.", contributor_id)
        return None
    ResourceBuilder.append_blank_tile_for_group(
        group_tile, A.ASSOCIATED_ORGANIZATION, {A.ASSOCIATED_ORGANIZATION: org}
    )
    contributor.save(force_admin=True, partial=True, index=False)
    return contributor


def seed_org(apps, schema_editor):
    org_id = next(iter(_org_ids()), None)
    if org_id:
        org = ResourceTileTree.get_tiles(GraphSlugs.CONTRIBUTOR).get(pk=org_id)
    else:
        org = ContributorBuilder(tag_as_seed=False).make_contributor(
            ContributorSpec(
                contributor_type=reference_value(
                    "contributor", "contributor_type", "Organization"
                ),
                first_name=None,
                name=ORG_NAME,
            )
        )
        logger.info("Created %r org %s", ORG_NAME, org.pk)

    contributors = ContributorService()
    linked = []
    group = Group.objects.filter(name=GROUP_NAME).first()
    members = group.user_set.all() if group else ()
    for user in members:
        contributor_id = contributors.username_contributor_id(user.username)
        if contributor_id:
            member = _link_member(contributor_id, org)
            if member is not None:
                linked.append(member)
    bulk_index([org, *linked])


def _delete_resource(resource_id):
    # index=False avoids the delete-time reindex of related resources (which
    # chokes on orphan-node drift); drop the resource's own search doc directly.
    Resource.objects.get(pk=resource_id).delete(index=False)
    SearchEngineFactory().create().delete(index=RESOURCES_INDEX, id=str(resource_id))


def remove_org(apps, schema_editor):
    for org_id in _org_ids():
        _delete_resource(org_id)


def _specs():
    return [spec for module in supported_permit_types() for spec in flatten(module)]


def seed_modules(apps, schema_editor):
    for template in ProcessRequirementService()._templates_by_id().values():
        _delete_resource(template.pk)
    builder = RequirementFlowBuilder()
    with builder.deferred_descriptors():
        templates = [
            builder.make_process_requirement({**spec, "is_template": True})
            for spec in _specs()
        ]
    _bulk_index(templates)


def remove_module_templates(apps, schema_editor):
    by_id = ProcessRequirementService()._templates_by_id()
    for spec in _specs():
        template = by_id.get(spec["id"])
        if template is not None:
            _delete_resource(template.pk)


class Migration(migrations.Migration):

    # The builder opens its own durable atomic block per save; can't nest.
    atomic = False

    dependencies = [
        ("bcap", "1423_seed_requirement_templates"),
    ]

    operations = [
        migrations.RunPython(seed_contributor_type_list, migrations.RunPython.noop),
        migrations.RunPython(seed_org, remove_org),
        migrations.RunPython(seed_modules, remove_module_templates),
    ]
