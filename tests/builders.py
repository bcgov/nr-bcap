"""A builder combining the domain mixins, for tests that build several resource
types through one builder (as the pre-split ResourceBuilder did)."""

from django.test import RequestFactory

from bcap.builders.contributor_builder import ContributorBuilder
from bcap.builders.process_requirement_builder import ProcessRequirementBuilder
from bcap.util.dashboard.dashboard_seed import DashboardDemoBuilder


class FixtureBuilder(ProcessRequirementBuilder, ContributorBuilder):
    pass


def request_as(user):
    """A request from this user, for services a view would hand its own."""
    request = RequestFactory().post("/")
    request.user = user
    return request


class SmallDashboardBuilder(DashboardDemoBuilder):
    """The demo builder with its shared pools cut to the minimum a card draws
    from, so tests exercise the same code without seeding a demo-sized dataset.
    The assignee pool has to cover one assignee per requirement."""

    _HOLDER_COUNT = 1
    _ASSIGNEE_POOL_SIZE = len(DashboardDemoBuilder._REQUIREMENTS)
    _HCA_POOL_SIZE = 1
    _OFFICER_POOL_SIZE = 1
