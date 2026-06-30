"""Builds contributor resources from a ContributorSpec."""

from dataclasses import dataclass

from bcap.builders.resource_builder import ResourceBuilder
from bcap.util.aliases.contributor import (
    ContributorAliases as aliases,
    ContributorGroupAliases as groups,
)
from bcap.util.bcap_aliases import GraphSlugs


@dataclass
class ContributorSpec:
    """Fields for a contributor resource."""

    contributor_type: object
    first_name: object  # None for an organization
    name: object
    bcap_username: object = None  # maps the contributor to a BCAP user
    associated_organization: object = None  # the organization it belongs to
    inactive: object = None  # the inactive flag on the contributor tile
    start_date: object = None  # membership start on the associated_organization tile
    end_date: object = None  # membership end on the associated_organization tile


class ContributorBuilder(ResourceBuilder):
    """Construct contributor resources."""

    def make_contributor(self, spec: ContributorSpec):
        """Create and return a contributor resource from its spec."""
        contributor = self.new_resource(GraphSlugs.CONTRIBUTOR)
        contributor_tile = self.append_blank_tile_for_group(
            contributor,
            groups.CONTRIBUTOR,
            {
                aliases.FIRST_NAME: (
                    self.localized(spec.first_name) if spec.first_name else None
                ),
                aliases.CONTRIBUTOR_NAME: self.localized(spec.name),
                aliases.CONTRIBUTOR_TYPE: spec.contributor_type,
                aliases.BCAP_USERNAME: spec.bcap_username,
                aliases.INACTIVE: spec.inactive,
            },
        )
        if spec.associated_organization is not None:
            self.append_blank_tile_for_group(
                contributor_tile,
                aliases.ASSOCIATED_ORGANIZATION,
                {
                    aliases.ASSOCIATED_ORGANIZATION: spec.associated_organization,
                    aliases.START_DATE: spec.start_date,
                    aliases.END_DATE: spec.end_date,
                },
            )
        contributor.save(**self.save_kwargs)
        self.claim(contributor)
        return contributor
