"""Contributor fixtures shared by the contributor and organization tests."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from bcap.permissions.groups import Groups
from bcap.builders.contributor_builder import ContributorSpec
from bcap.util.controlled_list import reference_value

from tests.builders import FixtureBuilder


def make_contributor(builder, name, first_name=None, **kwargs):
    """A Contributor; first_name=None makes an organization."""
    return builder.make_contributor(
        ContributorSpec(
            reference_value("contributor", "contributor_type"),
            first_name,
            name,
            **kwargs,
        )
    )


def make_user(username, internal=False):
    """A user, in the Resource Editor group when internal."""
    user = get_user_model().objects.create_user(username=username, password="pass")
    if internal:
        user.groups.add(Group.objects.get(name=Groups.RESOURCE_EDITOR))
    return user


def make_party(builder, username, first_name, name, internal=False, **kwargs):
    """A user and the Contributor that links to them by bcap_username -- the
    pairing every message/dashboard fixture needs, since party membership and
    assignment are both looked up through the Contributor."""
    return make_user(username, internal), make_contributor(
        builder, name, first_name, bcap_username=username, **kwargs
    )


def days_from_today(days):
    """An ISO date offset from today, for membership start/end bounds."""
    return (date.today() + timedelta(days=days)).isoformat()


# Wide windows so the UTC-vs-local boundary between the service's "today" and the
# test's never matters.
ACTIVE = {"start_date": days_from_today(-30), "end_date": days_from_today(30)}
EXPIRED = {"start_date": days_from_today(-60), "end_date": days_from_today(-30)}
FUTURE = {"start_date": days_from_today(30), "end_date": days_from_today(60)}


class ContributorFixtureMixin:
    """Builds Contributors and their organization memberships."""

    def setUp(self):
        super().setUp()
        self.builder = FixtureBuilder()
        self.contributor_type = reference_value("contributor", "contributor_type")

    def make(self, name, first_name=None, **kwargs):
        """Create a contributor; first_name=None makes an organization."""
        spec = ContributorSpec(self.contributor_type, first_name, name, **kwargs)
        return self.builder.make_contributor(spec)

    def make_with_orgs(self, name, memberships, first_name=None, bcap_username=None):
        """Create a contributor with one associated_organization tile per
        (organization, date-window) in ``memberships``."""
        builder = self.builder
        contributor = builder.new_resource("contributor")
        tile = builder.append_blank_tile_for_group(
            contributor,
            "contributor",
            {
                "first_name": builder.localized(first_name) if first_name else None,
                "contributor_name": builder.localized(name),
                "contributor_type": self.contributor_type,
                "bcap_username": bcap_username,
                "inactive": None,
            },
        )
        for org, window in memberships:
            builder.append_blank_tile_for_group(
                tile,
                "associated_organization",
                {"associated_organization": org, **window},
            )
        contributor.save(**builder.save_kwargs)
        return contributor
