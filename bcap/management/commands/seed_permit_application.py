"""Persist a Permit Application carrying the real-world process-requirement
flow (Recommend Referral / Recommend Decision / Decision Summary, with their
full sub-requirement checklists) to the current database, so the dashboard can
be viewed against production-shaped requirement data.

Temporary: a developer aid for building out the dashboard; will be removed in a
future release."""

from bcap.management.commands._dashboard_seed_base import DashboardSeedCommand
from bcap.util.dashboard.requirement_flow_seed import RequirementFlowBuilder


class Command(DashboardSeedCommand):
    builder_class = RequirementFlowBuilder
    help = (
        "Create a Permit Application carrying the real-world process-requirement "
        "flow (and its related HCA Permit and Contributors) in the current "
        "database. Temporary developer aid; will be removed in a future release."
    )
