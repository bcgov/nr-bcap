from dataclasses import dataclass

from django.db import transaction
from django.db.models import Q, TextField, UUIDField, Value
from django.db.models.fields.json import KeyTextTransform, KeyTransform
from django.db.models.functions import Cast, Coalesce
from django.utils import timezone

from arches.app.models.models import Node, TileModel

from arches_controlled_lists.models import ListItemValue

from bcap.services.dashboard.base_graph_service import BaseGraphService
from bcap.util.aliases.contributor import ContributorAliases
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.dashboard.resource_builder import ResourceBuilder
from bcap.util.user import full_name

INVITABLE_LIMIT = 30


@dataclass
class NewContributor:
    """A Contributor to create as part of an invite, for an invitee who has no
    record yet."""

    name: str
    email: str = ""
    first_name: str = ""  # given name, for a person
    # controlled-list item id; blank defaults to the Individual type at creation.
    contributor_type: str = ""


class ContributorService(BaseGraphService):
    """Reads Contributor resources for the dashboard's assignment filters
    (user-to-Contributor, company membership, display names), and the writes the
    admin invite flow needs: creating Contributors and binding a user to one."""

    A = ContributorAliases

    def username_contributor_id(self, username):
        """Id of the active Contributor with this bcap_username, or None."""
        username_node, contributor_ng = self._node_info(
            GraphSlugs.CONTRIBUTOR, self.A.BCAP_USERNAME
        )
        inactive_node = self._node_id(GraphSlugs.CONTRIBUTOR, self.A.INACTIVE)
        pk = (
            TileModel.objects.filter(
                nodegroup_id=contributor_ng,
                **{f"data__{username_node}": username},
            )
            .exclude(**{f"data__{inactive_node}": True})
            .values_list("resourceinstance_id", flat=True)
            .first()
        )
        return str(pk) if pk else None

    def company_contributor_ids(self, username):
        """The viewer plus the active members of every org the viewer actively
        belongs to today, excluding any flagged inactive."""
        if not username:
            return set()
        my_contributor_id = self.username_contributor_id(username)
        if not my_contributor_id:
            return set()

        org_node = self._node_id(GraphSlugs.CONTRIBUTOR, self.A.ASSOCIATED_ORGANIZATION)
        start_node = self._node_id(GraphSlugs.CONTRIBUTOR, self.A.START_DATE)
        end_node = self._node_id(GraphSlugs.CONTRIBUTOR, self.A.END_DATE)
        inactive_node, contributor_ng = self._node_info(
            GraphSlugs.CONTRIBUTOR, self.A.INACTIVE
        )
        membership_ng = self._node_info(
            GraphSlugs.CONTRIBUTOR, self.A.ASSOCIATED_ORGANIZATION
        )[1]
        today = timezone.now().date().isoformat()

        # Memberships active today (an unset start/end bound left open), each
        # tagged with the org it points at.
        active = (
            TileModel.objects.filter(nodegroup_id=membership_ng)
            .annotate(
                _start=Coalesce(
                    KeyTextTransform(start_node, "data"),
                    Value("0000-01-01"),
                    output_field=TextField(),
                ),
                _end=Coalesce(
                    KeyTextTransform(end_node, "data"),
                    Value("9999-12-31"),
                    output_field=TextField(),
                ),
                org=Cast(
                    KeyTextTransform(
                        "resourceId", KeyTransform("0", KeyTransform(org_node, "data"))
                    ),
                    UUIDField(),
                ),
            )
            .filter(_start__lte=today, _end__gte=today)
        )

        my_orgs = active.filter(resourceinstance_id=my_contributor_id).values("org")
        colleagues = active.filter(org__in=my_orgs).values("resourceinstance_id")

        # The viewer and the active members of those orgs, minus anyone inactive.
        company = (
            TileModel.objects.filter(nodegroup_id=contributor_ng)
            .filter(
                Q(resourceinstance_id=my_contributor_id)
                | Q(resourceinstance_id__in=colleagues)
            )
            .exclude(**{f"data__{inactive_node}": True})
            .values_list("resourceinstance_id", flat=True)
        )
        return {str(pk) for pk in company}

    def names_by_contributor_id(self, ids):
        """Map Contributor id -> "First Last" display name, blank parts skipped."""
        ids = set(ids)
        if not ids:
            return {}
        resources = self._resources(
            GraphSlugs.CONTRIBUTOR,
            ids,
            [self.A.FIRST_NAME, self.A.CONTRIBUTOR_NAME],
        )
        names = {}
        for c in resources:
            data = c.aliased_data.contributor.aliased_data
            first = data.first_name["display_value"]
            last = data.contributor_name["display_value"]
            names[str(c.pk)] = full_name(first, last)
        return names

    def _contributor_tile(self, contributor_id, lock=False):
        """The single Contributor group tile of a resource, or None. Pass
        lock=True to select it for update within a transaction."""
        contributor_ng = self._nodegroup_id(
            GraphSlugs.CONTRIBUTOR, self.A.BCAP_USERNAME
        )
        tiles = TileModel.objects.select_for_update() if lock else TileModel.objects
        return tiles.filter(
            resourceinstance_id=contributor_id, nodegroup_id=contributor_ng
        ).first()

    def is_invitable(self, contributor_id):
        """True when the Contributor exists, is active, and isn't already linked
        to a user account."""
        tile = self._contributor_tile(contributor_id)
        if tile is None:
            return False
        username_node = self._node_id(GraphSlugs.CONTRIBUTOR, self.A.BCAP_USERNAME)
        inactive_node = self._node_id(GraphSlugs.CONTRIBUTOR, self.A.INACTIVE)
        return not tile.data.get(inactive_node) and not tile.data.get(username_node)

    def set_bcap_username(self, contributor_id, username):
        """Stamp the username onto the Contributor's tile, but only if it isn't
        already linked. False when another account already holds it."""
        username_node = self._node_id(GraphSlugs.CONTRIBUTOR, self.A.BCAP_USERNAME)
        with transaction.atomic():
            tile = self._contributor_tile(contributor_id, lock=True)
            if tile is None or tile.data.get(username_node):
                return False
            tile.data[username_node] = username
            tile.save()
        return True

    def create_contributor(self, new_contributor: NewContributor):
        """Create a Contributor resource from the invite details and return its
        id. Created unlinked (no bcap_username) so the invite can bind it."""
        builder = ResourceBuilder(skip_refresh=False)
        resource = builder.new_resource(GraphSlugs.CONTRIBUTOR)
        resource.legacyid = None  # real data, not seed-marked
        contributor_type = (
            new_contributor.contributor_type or self._individual_type_id()
        )
        builder.append_blank_tile_for_group(
            resource,
            "contributor",  # the top-level group tile holding the leaf fields
            {
                self.A.CONTRIBUTOR_NAME: builder.localized(new_contributor.name),
                self.A.FIRST_NAME: (
                    builder.localized(new_contributor.first_name)
                    if new_contributor.first_name
                    else None
                ),
                self.A.CONTRIBUTOR_TYPE: [str(contributor_type)],
                self.A.CONTACT_EMAIL: builder.localized(new_contributor.email),
            },
        )
        resource.save(**builder.save_kwargs)
        return str(resource.pk)

    def delete_contributor(self, contributor_id):
        """Remove a Contributor resource, to roll back one created for an
        invite whose redemption then failed."""
        TileModel.objects.filter(
            resourceinstance_id=contributor_id
        ).first().resourceinstance.delete()

    def invitable_contributors(self, search=""):
        """Active, unlinked Contributors whose name matches the search, as
        {id, name, email, type} option dicts for the invite picker."""
        name_node, contributor_ng = self._node_info(
            GraphSlugs.CONTRIBUTOR, self.A.CONTRIBUTOR_NAME
        )
        username_node = self._node_id(GraphSlugs.CONTRIBUTOR, self.A.BCAP_USERNAME)
        inactive_node = self._node_id(GraphSlugs.CONTRIBUTOR, self.A.INACTIVE)

        tiles = (
            TileModel.objects.filter(nodegroup_id=contributor_ng)
            .exclude(**{f"data__{inactive_node}": True})
            .annotate(_username=KeyTextTransform(username_node, "data"))
            .filter(Q(_username__isnull=True) | Q(_username=""))
        )
        if search:
            tiles = tiles.filter(**{f"data__{name_node}__en__value__icontains": search})
        capped = tiles.values_list("resourceinstance_id", flat=True)[:INVITABLE_LIMIT]
        ids = [str(pk) for pk in capped]
        if not ids:
            return []

        resources = self._resources(
            GraphSlugs.CONTRIBUTOR,
            ids,
            [
                self.A.FIRST_NAME,
                self.A.CONTRIBUTOR_NAME,
                self.A.CONTACT_EMAIL,
                self.A.CONTRIBUTOR_TYPE,
            ],
        )

        def format_data(c):
            fields = c.aliased_data.contributor.aliased_data
            return {
                "id": str(c.pk),
                "name": full_name(
                    self._display_text(fields.first_name),
                    self._display_text(fields.contributor_name),
                ),
                "email": self._display_text(fields.contact_email),
                "type": self._display_text(fields.contributor_type),
            }

        return [format_data(c) for c in resources]

    def _individual_type_id(self):
        """The contributor_type list-item id for individuals, the only type the
        invite flow creates."""
        node = Node.objects.get(
            graph__slug=GraphSlugs.CONTRIBUTOR,
            alias=self.A.CONTRIBUTOR_TYPE,
            source_identifier=None,
        )
        return str(
            ListItemValue.objects.get(
                list_item__list_id=node.config.get("controlledList"),
                valuetype_id="prefLabel",
                value="Individual",
            ).list_item_id
        )
