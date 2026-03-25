from __future__ import annotations

import uuid

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
