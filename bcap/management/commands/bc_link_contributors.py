"""Link auth users to Contributor resources by matching first/last name, creating
new Contributor resources for any auth user without a matching record."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from arches.app.models.models import TileModel
from arches.app.models.resource import Resource
from arches_querysets.models import ResourceTileTree

from bcap.builders.contributor_builder import ContributorBuilder, ContributorSpec
from bcap.builders.resource_builder import ResourceBuilder
from bcap.permissions.groups import Groups
from bcap.services.contributor.contributor_service import ContributorService
from bcap.util.controlled_list import reference_value
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.aliases.contributor import ContributorAliases
from bcap.util.graph import node_id, nodegroup_id
from bcap.util.i18n import localized, localized_string
from bcap.util.indexing import bulk_index
from bcap.util.tiles import resource_instance_value


class Command(BaseCommand):
    """Match every auth user to a Contributor resource by first+last name and
    stamp their username onto it. Creates a new Contributor for any auth user
    that has no matching record."""

    help = "Link auth users to Contributor resources, creating missing records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Report what would happen without writing any changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write("Dry run — no changes will be written.\n")

        username_ng = nodegroup_id(
            GraphSlugs.CONTRIBUTOR, ContributorAliases.BCAP_USERNAME
        )
        username_node = node_id(
            GraphSlugs.CONTRIBUTOR, ContributorAliases.BCAP_USERNAME
        )
        name_node = node_id(GraphSlugs.CONTRIBUTOR, ContributorAliases.CONTRIBUTOR_NAME)
        first_name_node = node_id(GraphSlugs.CONTRIBUTOR, ContributorAliases.FIRST_NAME)
        email_node = node_id(GraphSlugs.CONTRIBUTOR, ContributorAliases.CONTACT_EMAIL)
        individual_type = reference_value(
            GraphSlugs.CONTRIBUTOR, ContributorAliases.CONTRIBUTOR_TYPE, "Individual"
        )

        assoc_org_ng = nodegroup_id(
            GraphSlugs.CONTRIBUTOR, ContributorAliases.ASSOCIATED_ORGANIZATION
        )
        assoc_org_node = node_id(
            GraphSlugs.CONTRIBUTOR, ContributorAliases.ASSOCIATED_ORGANIZATION
        )

        service = ContributorService()
        builder = ContributorBuilder(tag_as_seed=False)

        # Fetch the Archaeology Branch org resource once for the whole run.
        org_id = service.archaeology_branch_id()
        if org_id:
            org = ResourceTileTree.get_tiles(GraphSlugs.CONTRIBUTOR).get(pk=org_id)
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Archaeology Branch contributor not found; org will not be linked.\n"
                )
            )
            org = None

        users = list(User.objects.all())
        self.stdout.write(f"Found {len(users)} auth users\n")

        matched = []
        created = []
        skipped = []
        to_index = []

        for user in users:
            if not user.first_name or not user.last_name:
                skipped.append(user.username)
                continue

            is_archaeology_branch = (
                org is not None
                and user.groups.filter(name=Groups.ARCHAEOLOGY_BRANCH).exists()
            )

            tile = TileModel.objects.filter(
                nodegroup_id=username_ng,
                **{
                    f"data__{name_node}__en__value__iexact": user.last_name,
                    f"data__{first_name_node}__en__value__iexact": user.first_name,
                },
            ).first()

            if tile:
                contributor_id = str(tile.resourceinstance_id)
                existing_username = tile.data.get(username_node)
                status_parts = []
                if existing_username:
                    status_parts.append(f"already linked to '{existing_username}'")
                elif not dry_run:
                    success = service.set_bcap_username(contributor_id, user.username)
                    status_parts.append("updated" if success else "failed")
                    # Re-fetch after set_bcap_username saves, so the email update
                    # below doesn't overwrite the username just written.
                    if success:
                        tile = TileModel.objects.get(pk=tile.pk)
                else:
                    status_parts.append("would update")

                if user.email and not localized_string(tile.data.get(email_node)):
                    if not dry_run:
                        tile.data[email_node] = localized(user.email)
                        tile.save()
                        status_parts.append("email set")
                    else:
                        status_parts.append("would set email")

                if is_archaeology_branch:
                    existing_org_tile = TileModel.objects.filter(
                        resourceinstance_id=contributor_id,
                        nodegroup_id=assoc_org_ng,
                    ).first()
                    correct_org = (
                        existing_org_tile is not None
                        and existing_org_tile.data.get(assoc_org_node)
                        and TileModel.objects.filter(
                            pk=existing_org_tile.pk,
                            data__contains={
                                assoc_org_node: resource_instance_value(org_id)
                            },
                        ).exists()
                    )
                    if correct_org:
                        status_parts.append("org already set")
                    elif existing_org_tile is not None:
                        # Tile exists but org value is null or wrong — overwrite it.
                        if not dry_run:
                            existing_org_tile.data[assoc_org_node] = (
                                resource_instance_value(org_id)
                            )
                            existing_org_tile.save()
                            to_index.append(Resource.objects.get(pk=contributor_id))
                            status_parts.append("org updated")
                        else:
                            status_parts.append("would update org")
                    elif not dry_run:
                        contributor = ResourceTileTree.get_tiles(
                            GraphSlugs.CONTRIBUTOR
                        ).get(pk=contributor_id)
                        group_tile = contributor.aliased_data.contributor
                        if group_tile is not None:
                            ResourceBuilder.append_blank_tile_for_group(
                                group_tile,
                                ContributorAliases.ASSOCIATED_ORGANIZATION,
                                {ContributorAliases.ASSOCIATED_ORGANIZATION: org},
                            )
                            contributor.save(
                                force_admin=True, partial=True, index=False
                            )
                            to_index.append(contributor)
                            status_parts.append("org linked")
                        else:
                            status_parts.append("org link failed: no group tile")
                    else:
                        status_parts.append("would link org")

                matched.append((user.username, contributor_id, ", ".join(status_parts)))
            else:
                if not dry_run:
                    contributor = builder.make_contributor(
                        ContributorSpec(
                            contributor_type=individual_type,
                            first_name=user.first_name,
                            name=user.last_name,
                            email=user.email,
                            bcap_username=user.username,
                            associated_organization=(
                                org if is_archaeology_branch else None
                            ),
                        )
                    )
                    to_index.append(contributor)
                    created.append((user.username, str(contributor.pk)))
                else:
                    created.append((user.username, "(dry run)"))

        if not dry_run and to_index:
            bulk_index(to_index)

        self.stdout.write("\n=== Matched existing contributors ===")
        for username, cid, status in matched:
            self.stdout.write(f"  {username} -> {cid} ({status})")

        self.stdout.write(
            f"\n=== {'Would create' if dry_run else 'Created'} new contributors ({len(created)}) ==="
        )
        for username, cid in created:
            self.stdout.write(f"  {username} -> {cid}")

        self.stdout.write(f"\nSkipped (no first/last name): {skipped}")
