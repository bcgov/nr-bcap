from __future__ import annotations

from typing_extensions import Any
from unittest.mock import MagicMock

from shared import _make_bool, _uuid  # noqa: F401


def _make_node(
    datatype: str = "string",
    node_id: str | None = None,
    nodegroup_id: str | None = None,
) -> MagicMock:
    node = MagicMock()
    node.datatype = datatype
    node.nodeid = node_id or _uuid()
    node.nodegroup_id = nodegroup_id or _uuid()
    return node


def _make_tile(
    data: dict[str, Any] | None = None,
    nodegroup_id: str | None = None,
    resource_id: str | None = None,
) -> dict[str, Any]:
    return {
        "data": data or {},
        "nodegroup_id": nodegroup_id or _uuid(),
        "resourceinstance_id": resource_id or _uuid(),
    }
