from __future__ import annotations

import uuid

from typing_extensions import Any
from unittest.mock import MagicMock


def _uuid() -> str:
    return str(uuid.uuid4())


def _make_bool(must: list | None = None, should: list | None = None, must_not: list | None = None) -> MagicMock:
    mock = MagicMock()
    mock.dsl = {
        "bool": {
            "must": must or [],
            "must_not": must_not or [],
            "should": should or [],
        }
    }
    return mock


def _make_node(datatype: str = "string", node_id: str | None = None, nodegroup_id: str | None = None) -> MagicMock:
    node = MagicMock()
    node.datatype = datatype
    node.nodeid = node_id or _uuid()
    node.nodegroup_id = nodegroup_id or _uuid()
    return node


def _make_tile(resource_id: str | None = None, nodegroup_id: str | None = None, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "data": data or {},
        "resourceinstance_id": resource_id or _uuid(),
        "nodegroup_id": nodegroup_id or _uuid(),
    }
