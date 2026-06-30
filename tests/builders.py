"""A builder combining the domain mixins, for tests that build several resource
types through one builder (as the pre-split ResourceBuilder did)."""

from bcap.builders.contributor_builder import ContributorBuilder
from bcap.builders.process_requirement_builder import ProcessRequirementBuilder


class FixtureBuilder(ProcessRequirementBuilder, ContributorBuilder):
    pass
