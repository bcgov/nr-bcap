"""Builder for the real process-requirement templates: non-randomized names,
not tagged as deletable seed data. Reuses the demo builder's resource
primitives; callers pass the specs to build from."""

from bcap.util.dashboard.dashboard_seed import DashboardDemoBuilder


class RequirementFlowBuilder(DashboardDemoBuilder):
    """Build real process-requirement templates. Differs from the demo builder
    only in flags; graph assembly is inherited."""

    _SEED_UNASSIGNED_PERMIT = False
    _RANDOMIZE_NAME = False
    _TAG_AS_SEED = False
