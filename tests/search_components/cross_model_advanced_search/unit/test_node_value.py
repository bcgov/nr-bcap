from __future__ import annotations

import pytest
from typing_extensions import Any

from bcap.search_components.cross_model_advanced_search import NodeValue


class TestNodeValue:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ({"resourceId": "abc-123"}, {"abc-123"}),
            ({"resourceId": "abc-123", "otherField": "xyz"}, {"abc-123"}),
            ({"resourceId": None}, {None}),
            ({"resourceId": ""}, {""}),
            ({"resourceId": 42}, {42}),
            ({"ResourceId": "abc-123"}, set()),
            ({"resourceid": "abc-123"}, set()),
            ({}, set()),
            (
                [{"resourceId": "abc-123"}, {"resourceId": "def-456"}],
                {"abc-123", "def-456"},
            ),
            ([{"resourceId": "abc-123"}, {"resourceId": "abc-123"}], {"abc-123"}),
            ([{"otherId": "abc"}, {"resourceId": "def-456"}], {"def-456"}),
            ([{"resourceId": "abc"}, {"somethingElse": "xyz"}, None], {"abc"}),
            ([None, {"resourceId": "abc"}, None], {"abc"}),
            (["not-a-dict", 123, None], set()),
            ([None, None, None], set()),
            ([{}, {}, {}], set()),
            ([[{"resourceId": "abc"}]], set()),
            ([], set()),
            (None, set()),
            ("just-a-string", set()),
            (42, set()),
            (3.14, set()),
            (True, set()),
            (False, set()),
            (0, set()),
            (({"resourceId": "abc"},), set()),
            ({"a", "b"}, set()),
        ],
    )
    def test_extract(self, raw: Any, expected: set) -> None:
        assert NodeValue(raw=raw).extract() == expected
