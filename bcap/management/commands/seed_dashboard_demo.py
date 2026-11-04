"""Persist the dashboard demo graph (the same data the dashboard service tests
build) to the current database so it can be viewed in the app.

Temporary: this is a developer aid for building out the dashboard and will be
removed in a future release."""

from bcap.management.commands._dashboard_seed_base import DashboardSeedCommand
from bcap.util.dashboard.dashboard_seed import DashboardDemoBuilder


class Command(DashboardSeedCommand):
    builder_class = DashboardDemoBuilder
    help = (
        "Create the dashboard demo Permit Application (and its related Process "
        "Requirement, HCA Permit, and Contributors) in the current database. "
        "Temporary developer aid; will be removed in a future release."
    )
