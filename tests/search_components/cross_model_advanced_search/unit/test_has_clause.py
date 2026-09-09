from __future__ import annotations

import pytest

from bcap.search_components.cross_model_advanced_search import has_clause
from helper import _make_bool

_TERM = {"term": {"field": "value"}}


class TestHasClause:
    @pytest.mark.parametrize(
        "clauses,expected",
        [
            ({}, False),
            ({"must": [], "should": [], "must_not": []}, False),
            ({"must": [_TERM]}, True),
            ({"should": [_TERM]}, True),
            ({"must_not": [_TERM]}, True),
            ({"must": [], "should": [_TERM]}, True),
            ({"must": [], "should": [], "must_not": [_TERM]}, True),
            ({"must": [_TERM], "should": [_TERM], "must_not": [_TERM]}, True),
        ],
    )
    def test_has_clause(self, clauses: dict[str, list], expected: bool) -> None:
        assert has_clause(_make_bool(**clauses)) is expected
