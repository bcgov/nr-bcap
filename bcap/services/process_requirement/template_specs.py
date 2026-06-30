"""Process-requirement group specs, one JSON file per permit type under
pkg/reference_data/process_requirements/groups. Each file is a grouping parent
with its child requirements nested under requirements in flow order. The JSON is
the single source of the requirement names, shared by the seed migration and the
runtime clone-and-attach."""

import json
from pathlib import Path

from django.apps import apps


def _root():
    return (
        Path(apps.get_app_config("bcap").path)
        / "pkg"
        / "reference_data"
        / "process_requirements"
        / "groups"
    )


def supported_permit_types():
    """The permit types that have a template file."""
    return sorted(path.stem for path in _root().glob("*.json"))


def load(permit_type):
    """A permit type's grouping parent spec, with its child requirements nested
    under ``requirements`` in flow order."""
    if permit_type not in supported_permit_types():
        raise FileNotFoundError(f"No template spec for permit type '{permit_type}'.")
    return json.loads((_root() / f"{permit_type}.json").read_text())


def flatten(permit_type):
    """A permit type's specs as a flat list for seeding: the grouping parent
    followed by its child requirements, in flow order."""
    parent = load(permit_type)
    children = parent.pop("requirements")
    return [parent, *children]


def host_graph(permit_type):
    """The graph a module populates from the submit payload: the child whose
    resource matches the module slug, or None when the type has no group file or
    no such host child."""
    if permit_type not in supported_permit_types():
        return None
    children = load(permit_type)["requirements"]
    return next(
        (c["resource"] for c in children if c["resource"] == permit_type),
        None,
    )
