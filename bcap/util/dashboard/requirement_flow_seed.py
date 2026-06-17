"""Builds the real-world process-requirement flow (Recommend Referral, Recommend
Decision, Decision Summary) with full sub-requirement checklists, from the
reference-data specs. Reuses the demo builder; only the requirement specs
differ."""

from bcap.util.dashboard.dashboard_seed import DashboardDemoBuilder
import os
import json
from django.apps import apps
from pathlib import Path


class RequirementFlowBuilder(DashboardDemoBuilder):
    """Build one permit carrying the full real-world requirement flow. Only the
    requirement specs differ from the demo builder; assignees, holders, and
    graph assembly are inherited."""

    _SEED_UNASSIGNED_PERMIT = False
    _RANDOMIZE_NAME = False
    _TAG_AS_SEED = False
    _ROOT_DIR = (
        Path(apps.get_app_config("bcap").path)
        / "pkg"
        / "reference_data"
        / "process_requirements"
    )
    # Only doing this for now so the files can be ordered
    _FILES = [
        "recommend_referral.json",
        "recommend_decision.json",
        "decision_summary.json",
    ]

    @staticmethod
    def _get_requirement_specs(root_dir, files):
        dicts = []
        for json_file in files:
            with open(os.path.join(root_dir, json_file)) as f:
                dicts.append(json.load(f))
        return dicts

    _REQUIREMENTS = _get_requirement_specs(_ROOT_DIR, _FILES)
