import os
import sys
import unittest
from pathlib import Path

from arches.test.runner import ArchesTestRunner
from arches.app.search.mappings import (
    prepare_terms_index,
    delete_terms_index,
    prepare_concepts_index,
    delete_concepts_index,
    prepare_search_index,
    delete_search_index,
)

_CROSS_MODEL_ROOT = (
    Path(__file__).parent / "search_components" / "cross_model_advanced_search"
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
    def _find_test_path(self, full_path, pattern, *args, **kwargs):
        if os.path.isdir(full_path) and os.path.basename(full_path) == "integration":
            return None, False
        return super()._find_test_path(full_path, pattern, *args, **kwargs)


class BcapTestRunner(ArchesTestRunner):
    def setup_databases(self, **kwargs):
        """Create the ES indices (at Arches' 50000-field limit) before migrations.

        ArchesTestRunner prepares them only after super().setup_databases(), but
        0002_load_package runs during that call: each graph.save() bare-creates
        the ``resources`` index at Elasticsearch's 1000-field default, which the
        bcap graphs exceed, aborting the load. Pre-creating fixes the limit first.
        """
        if kwargs.get("aliases"):
            delete_terms_index()
            delete_concepts_index()
            delete_search_index()
            prepare_terms_index(create=True)
            prepare_concepts_index(create=True)
            prepare_search_index(create=True)
        return super().setup_databases(**kwargs)

    def build_suite(self, test_labels=None, **kwargs):
        for p in _CONFTEST_PATHS:
            if p not in sys.path:
                sys.path.insert(0, p)
        self.test_loader = _ExcludeIntegrationLoader()
        return super().build_suite(test_labels, **kwargs)
