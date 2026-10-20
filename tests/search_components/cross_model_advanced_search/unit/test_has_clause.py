from __future__ import annotations

import pytest

from bcap.search_components.cross_model_advanced_search import has_clause
from helper import _make_bool

_TERM = {"term": {"field": "value"}}


class TestHasClause:
    @pytest.mark.parametrize(
        "clauses,expected",
        [
            pytest.param({}, False, id="empty_bool"),
            pytest.param(
                {"must": [], "should": [], "must_not": []},
                False,
                id="all_empty_lists",
            ),
            pytest.param({"must": [_TERM]}, True, id="with_must"),
            pytest.param({"should": [_TERM]}, True, id="with_should"),
            pytest.param({"must_not": [_TERM]}, True, id="with_must_not"),
            pytest.param(
                {"must": [], "should": [_TERM]},
                True,
                id="must_empty_should_populated",
            ),
            pytest.param(
                {"must": [], "should": [], "must_not": [_TERM]},
                True,
                id="only_must_not",
            ),
            pytest.param(
                {"must": [_TERM], "should": [_TERM], "must_not": [_TERM]},
                True,
                id="all_three_populated",
            ),
        ],
    )
    def test_has_clause(self, clauses: dict[str, list], expected: bool) -> None:
        assert has_clause(_make_bool(**clauses)) is expected
