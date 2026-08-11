"""
Sanity-check the checked-in graph JSON files for common node mis-configurations.

These tests run against the static package files and require no database access.
They catch environment-specific values (absolute URLs, wrong app prefixes,
wrong controlled-list-manager hosts) that must be corrected before merging.
"""

import json
import urllib.parse
from pathlib import Path

from django.apps import apps
from django.test import SimpleTestCase


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RESOURCE_INSTANCE_DATATYPES = frozenset({"resource-instance", "resource-instance-list"})

# searchStrings must be relative paths under /bcap/search, never absolute URLs
# and never paths from a different app (e.g. /bc-fossil-management/search).
REQUIRED_SEARCH_PREFIX = "/bcap/search"

# uri values embedded inside advanced-search filters must point to the local
# controlled-list-manager instance.
REQUIRED_URI_PREFIX = (
    "https://localhost/bcap/plugins/controlled-list-manager/item/"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resource_model_paths():
    pkg = Path(apps.get_app_config("bcap").path) / "pkg"
    return sorted((pkg / "graphs" / "resource_models").glob("*.json"))


def _all_nodes():
    """Yield (filename, alias, datatype, config) for every node in every resource model."""
    for path in _resource_model_paths():
        data = json.loads(path.read_text())
        for node in data["graph"][0].get("nodes", []):
            yield (
                path.name,
                node.get("alias", ""),
                node.get("datatype", ""),
                node.get("config") or {},
            )


def _uri_values_in_search_string(search_string):
    """
    Extract every reference-item ``uri`` value from the advanced-search JSON
    embedded in a searchString URL.

    Arches encodes controlled-list item filters as:

        advanced-search=[{"op":"and", "<node-id>": {"op":"eq",
            "val": [{"labels":[...], "uri":"https://..."}]}}]

    The ``val`` list carries the *default* filter values (pre-selected items
    that narrow the resource picker when the field is opened).
    Both percent-encoded and raw JSON forms are handled by parse_qs.
    """
    try:
        params = urllib.parse.parse_qs(urllib.parse.urlparse(search_string).query)
    except Exception:
        return []

    uris = []
    for raw in params.get("advanced-search", []):
        try:
            filters = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(filters, list):
            continue
        for filter_group in filters:
            for field_filter in filter_group.values():
                if not isinstance(field_filter, dict):
                    continue
                val = field_filter.get("val")
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict) and "uri" in item:
                            uris.append(item["uri"])
    return uris


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestResourceInstanceNodeSearchStrings(SimpleTestCase):
    """
    resource-instance and resource-instance-list nodes with a non-empty
    searchString must:

    1. Use a **relative** path starting with ``/bcap/search`` — never an
       absolute URL, and never a path from a different application.
    2. Be parseable as a URL.
    3. Embed only controlled-list-manager ``uri`` values that point to the
       local instance (``https://localhost/bcap/plugins/controlled-list-manager/item/``).
       These uri values are the *default* filter items that pre-populate the
       resource picker's search and must not contain host names from other
       environments.
    """

    def _configured_nodes(self):
        """Return (filename, alias, config) for RI nodes that have a non-empty searchString."""
        return [
            (filename, alias, config)
            for filename, alias, datatype, config in _all_nodes()
            if datatype in RESOURCE_INSTANCE_DATATYPES and config.get("searchString")
        ]

    def test_search_strings_start_with_bcap_search(self):
        """Non-empty searchStrings must be relative paths starting with /bcap/search."""
        failures = []
        for filename, alias, config in self._configured_nodes():
            ss = config["searchString"]
            if not ss.startswith(REQUIRED_SEARCH_PREFIX):
                failures.append(f"  {filename} / {alias}:\n    {ss!r}")
        if failures:
            self.fail(
                f"searchString must start with {REQUIRED_SEARCH_PREFIX!r}."
                f" {len(failures)} violation(s):\n" + "\n".join(failures)
            )

    def test_search_strings_are_parseable(self):
        """Non-empty searchStrings must be parseable as URLs with a non-empty path."""
        failures = []
        for filename, alias, config in self._configured_nodes():
            ss = config["searchString"]
            try:
                parsed = urllib.parse.urlparse(ss)
                if not parsed.path:
                    raise ValueError("empty path component")
            except Exception as exc:
                failures.append(f"  {filename} / {alias}: {exc}\n    {ss!r}")
        if failures:
            self.fail(
                f"searchString must be a parseable URL."
                f" {len(failures)} violation(s):\n" + "\n".join(failures)
            )

    def test_advanced_search_uri_values_use_local_clm(self):
        """
        uri values embedded in advanced-search filters (the default filter items)
        must reference the local controlled-list-manager instance.
        """
        failures = []
        for filename, alias, config in self._configured_nodes():
            ss = config["searchString"]
            for uri in _uri_values_in_search_string(ss):
                if not uri.startswith(REQUIRED_URI_PREFIX):
                    failures.append(f"  {filename} / {alias}:\n    {uri!r}")
        if failures:
            self.fail(
                f"uri values in advanced-search filters must start with"
                f" {REQUIRED_URI_PREFIX!r}."
                f" {len(failures)} violation(s):\n" + "\n".join(failures)
            )
