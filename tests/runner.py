import os
import sys
import unittest
from pathlib import Path

from arches.test.runner import ArchesTestRunner

_CROSS_MODEL_ROOT = (
    Path(__file__).parent
    / "search_components"
    / "cross_model_advanced_search"
)

# Directories that conftest.py files add to sys.path for pytest.
# The Django test runner never loads conftest.py, so we replicate it here
# so that bare imports like `from helper import ...` resolve correctly.
_CONFTEST_PATHS = [
    str(_CROSS_MODEL_ROOT),  # shared.py lives here
    str(_CROSS_MODEL_ROOT / "mock"),
    str(_CROSS_MODEL_ROOT / "unit"),
    str(_CROSS_MODEL_ROOT / "scenario"),
    str(_CROSS_MODEL_ROOT / "snapshot"),
]


class _ExcludeIntegrationLoader(unittest.TestLoader):
    def discover(self, start_dir, pattern="test*.py", top_level_dir=None):
        if os.path.basename(os.path.normpath(str(start_dir))) == "integration":
            return self.suiteClass()
        return super().discover(start_dir, pattern=pattern, top_level_dir=top_level_dir)


class BcapTestRunner(ArchesTestRunner):
    def build_suite(self, test_labels=None, **kwargs):
        for p in _CONFTEST_PATHS:
            if p not in sys.path:
                sys.path.insert(0, p)
        self.test_loader = _ExcludeIntegrationLoader()
        return super().build_suite(test_labels, **kwargs)
