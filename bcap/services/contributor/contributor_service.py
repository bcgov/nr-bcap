from dataclasses import dataclass
from functools import cached_property
from typing import Self

from django.db import transaction
from django.db.models import Q, TextField, UUIDField, Value
from django.db.models.fields.json import KeyTextTransform, KeyTransform
from django.db.models.functions import Cast, Coalesce
from django.utils import timezone

from arches.app.models.models import TileModel
from arches.app.models.resource import Resource

from bcap.services.dashboard.base_graph_service import BaseGraphService
from bcap.util.controlled_list import reference_value
from bcap.util.aliases.contributor import (
    ContributorAliases,
    ContributorGroupAliases,
)
from bcap.util.auth.groups import Groups, is_internal_username
from bcap.util.bcap_aliases import GraphSlugs
from bcap.builders.resource_builder import ResourceBuilder
from bcap.util.tiles import all_referenced_resource_ids
from bcap.util.user import last_first

INVITABLE_LIMIT = 30


@dataclass
class NewContributor:
    """A Contributor to create as part of an invite, for an invitee who has no
    record yet."""

    name: str
    email: str = ""
    phone: str = ""
    first_name: str = ""  # given name, for a person
    # controlled-list item id; blank defaults to the Individual type at creation.
    contributor_type: str = ""


@dataclass
class ContributorSummary:
    """A hydrated Contributor for display: id, "Last, First" name, and the email
    and type a picker shows to tell recipients apart."""

    id: str
    name: str
    email: str
    type: str

    @classmethod
    def from_resource(cls, resource) -> Self:
        """Read a summary off a contributor tree loaded with the by_ids aliases."""
        data = resource.aliased_data

        def text(alias):
            return BaseGraphService._display_text(
                BaseGraphService._node_value(data, alias)
            )

        return cls(
            id=str(resource.pk),
            name=last_first(
                text(ContributorAliases.FIRST_NAME),
                text(ContributorAliases.CONTRIBUTOR_NAME),
            ),
            email=text(ContributorAliases.CONTACT_EMAIL),
            type=text(ContributorAliases.CONTRIBUTOR_TYPE),
        )


class ContributorService(BaseGraphService):
    """Reads Contributor resources for the dashboard's assignment filters
    (user-to-Contributor, company membership, display names), and the writes the
    admin invite flow needs: creating Contributors and binding a user to one."""

    # Node ids for the contributor graph are fixed for the life of a request;
    # cache them so the read methods don't each re-resolve the same aliases.
    @cached_property
    def _username_node(self):
        return self.node_id(GraphSlugs.CONTRIBUTOR, ContributorAliases.BCAP_USERNAME)

    @cached_property
    def _contributor_ng(self):
        return self._nodegroup_id(
            GraphSlugs.CONTRIBUTOR, ContributorAliases.BCAP_USERNAME
        )

    @cached_property
    def _inactive_node(self):
        return self.node_id(GraphSlugs.CONTRIBUTOR, ContributorAliases.INACTIVE)

    def _active(self, queryset):
        """Drop tiles flagged inactive."""
        return queryset.exclude(**{f"data__{self._inactive_node}": True})

    def username_contributor_id(self, username):
        """Id of the active Contributor with this bcap_username, or None."""
        # Containment (data @> {...}) so the tiledata GIN index is used; plain
        # key equality (data__<node>=...) can't use it and seq-scans the table.
        pk = (
            self._active(
                TileModel.objects.filter(
                    nodegroup_id=self._contributor_ng,
                    data__contains={self._username_node: username},
                )
            )
            .values_list("resourceinstance_id", flat=True)
            .first()
        )
        return str(pk) if pk else None

    def login_linked_contributor_ids(self, ids=None):
        """Of the given resource ids, those that are active Contributors linked
        to a login (a bcap_username set), so they can sign in to read messages.
        Pass None for every login-linked Contributor."""
        tiles = self._active(
            TileModel.objects.filter(
                nodegroup_id=self._contributor_ng,
                data__has_key=self._username_node,
            )
        )
        if ids is not None:
            tiles = tiles.filter(resourceinstance_id__in=ids)
        pks = (
            tiles.annotate(_username=KeyTextTransform(self._username_node, "data"))
            .exclude(Q(_username__isnull=True) | Q(_username=""))
            .values_list("resourceinstance_id", flat=True)
        )
        return {str(pk) for pk in pks}

    def assignable_contributors(self) -> list[ContributorSummary]:
        """The pool an assignee is picked from: every Contributor with a login.
        Narrow to the ministry reviewer groups once role groups
        land, so applicants aren't offered as assignees."""
        return self.by_ids(self.login_linked_contributor_ids())

    def by_ids(self, ids) -> list[ContributorSummary]:
        """Load the given Contributors, name-sorted (id, "Last, First" name,
        email, type). The single contributor-read response shape:
        contributors_for_resource and invitable_contributors just pick the ids
        differently, and callers wanting a name lookup project {c.id: c.name}
        off the result."""
        ids = set(ids)
        if not ids:
            return []
        resources = self._tiles(
            GraphSlugs.CONTRIBUTOR,
            ids,
            [
                ContributorAliases.FIRST_NAME,
                ContributorAliases.CONTRIBUTOR_NAME,
                ContributorAliases.CONTACT_EMAIL,
                ContributorAliases.CONTRIBUTOR_TYPE,
            ],
        )
        options = [ContributorSummary.from_resource(c) for c in resources]
        return sorted(options, key=lambda o: o.name.lower())

    def archaeology_branch_id(self):
        """Resource id of the Archaeology Branch organization Contributor, or
        None when it hasn't been seeded."""
        name_node = self.node_id(
            GraphSlugs.CONTRIBUTOR, ContributorAliases.CONTRIBUTOR_NAME
        )
        pk = (
            self._active(
                TileModel.objects.filter(
                    nodegroup_id=self._contributor_ng,
                    data__contains={
                        name_node: {"en": {"value": Groups.ARCHAEOLOGY_BRANCH}}
                    },
                )
            )
            .values_list("resourceinstance_id", flat=True)
            .first()
        )
        return str(pk) if pk else None

    def contributors_for_resource(self, resource_id):
        """Pick-list options for a resource: its referenced contributors that
        have a login (ministry assignees included), name-sorted. Falls back to
        the Archaeology Branch when nobody is assigned, so there is always
        someone to address."""
        ids = self.login_linked_contributor_ids(
            all_referenced_resource_ids(resource_id)
        )
        if not ids:
            branch = self.archaeology_branch_id()
            ids = {branch} if branch else set()
        return self.by_ids(ids)

    def contributor_username(self, contributor_id):
        """The bcap_username linked to a Contributor, or None when it is unset
        or the Contributor has no tile."""
        username = (
            TileModel.objects.filter(
                nodegroup_id=self._contributor_ng,
                resourceinstance_id=contributor_id,
            )
            .values_list(f"data__{self._username_node}", flat=True)
            .first()
        )
        return username or None

    def contributor_is_internal(self, contributor_id):
        """True when the Contributor is linked to an internal (staff) user."""
        return is_internal_username(self.contributor_username(contributor_id))

    def _contributor_tile(self, contributor_id, lock=False):
        """The single Contributor group tile of a resource, or None. Pass
        lock=True to select it for update within a transaction."""
        tiles = TileModel.objects.select_for_update() if lock else TileModel.objects
        return tiles.filter(
            resourceinstance_id=contributor_id, nodegroup_id=self._contributor_ng
        ).first()

    def is_invitable(self, contributor_id):
        """True when the Contributor exists, is active, and isn't already linked
        to a user account."""
        tile = self._contributor_tile(contributor_id)
        if tile is None:
            return False
        return not tile.data.get(self._inactive_node) and not tile.data.get(
            self._username_node
        )

    def set_bcap_username(self, contributor_id, username):
        """Stamp the username onto the Contributor's tile, but only if it isn't
        already linked. False when another account already holds it."""
        with transaction.atomic():
            tile = self._contributor_tile(contributor_id, lock=True)
            if tile is None or tile.data.get(self._username_node):
                return False
            tile.data[self._username_node] = username
            tile.save()
        Resource.objects.get(pk=contributor_id).index()
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
            ContributorGroupAliases.CONTRIBUTOR,  # the top-level group tile holding the leaf fields
            {
                ContributorAliases.CONTRIBUTOR_NAME: builder.localized(
                    new_contributor.name
                ),
                ContributorAliases.FIRST_NAME: (
                    builder.localized(new_contributor.first_name)
                    if new_contributor.first_name
                    else None
                ),
                ContributorAliases.CONTRIBUTOR_TYPE: [str(contributor_type)],
                ContributorAliases.CONTACT_EMAIL: builder.localized(
                    new_contributor.email
                ),
                ContributorAliases.CONTACT_PHONE_NUMBER: (
                    builder.localized(new_contributor.phone)
                    if new_contributor.phone
                    else None
                ),
            },
        )
        # Index into Elasticsearch (save_kwargs default to index=False for bulk
        # seeding) so the new Contributor shows up in search and the dashboards.
        resource.save(**{**builder.save_kwargs, "index": True})
        return str(resource.pk)

    def delete_contributor(self, contributor_id):
        """Remove a Contributor resource, to roll back one created for an
        invite whose redemption then failed."""
        TileModel.objects.filter(
            resourceinstance_id=contributor_id
        ).first().resourceinstance.delete()

    def invitable_contributors(self, search=""):
        """Active, unlinked Contributors whose name matches the search, as
        name-sorted pick-list options for the invite picker."""
        name_node = self.node_id(
            GraphSlugs.CONTRIBUTOR, ContributorAliases.CONTRIBUTOR_NAME
        )

        tiles = (
            self._active(TileModel.objects.filter(nodegroup_id=self._contributor_ng))
            .annotate(_username=KeyTextTransform(self._username_node, "data"))
            .filter(Q(_username__isnull=True) | Q(_username=""))
        )
        if search:
            tiles = tiles.filter(**{f"data__{name_node}__en__value__icontains": search})
        capped = tiles.values_list("resourceinstance_id", flat=True)[:INVITABLE_LIMIT]
        return self.by_ids(capped)

    def _individual_type_id(self):
        """The contributor_type list-item id for individuals, the only type the
        invite flow creates."""
        return reference_value(
            GraphSlugs.CONTRIBUTOR,
            ContributorAliases.CONTRIBUTOR_TYPE,
            label="Individual",
        )[0]
