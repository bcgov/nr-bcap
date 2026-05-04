from __future__ import annotations

from bcap.search_components.cross_model_advanced_search import has_clause
from helper import _make_bool


class TestHasClause:
    def test_empty_bool(self) -> None:
        query = _make_bool()
        assert has_clause(query) is False

    def test_with_must(self) -> None:
        query = _make_bool(must=[{"term": {"field": "value"}}])
        assert has_clause(query) is True

    def test_with_should(self) -> None:
        query = _make_bool(should=[{"term": {"field": "value"}}])
        assert has_clause(query) is True

    def test_with_must_not(self) -> None:
        query = _make_bool(must_not=[{"term": {"field": "value"}}])
        assert has_clause(query) is True

    def test_all_empty_lists(self) -> None:
        query = _make_bool(must=[], should=[], must_not=[])
        assert has_clause(query) is False

    def test_must_and_should(self) -> None:
        query = _make_bool(
            must=[{"term": {"a": 1}}],
            should=[{"term": {"b": 2}}],
        )
        assert has_clause(query) is True

    def test_all_three_populated(self) -> None:
        query = _make_bool(
            must=[{"term": {"a": 1}}],
            should=[{"term": {"b": 2}}],
            must_not=[{"term": {"c": 3}}],
        )
        assert has_clause(query) is True

    def test_only_must_not(self) -> None:
        query = _make_bool(must=[], should=[], must_not=[{"term": {"x": 1}}])
        assert has_clause(query) is True

    def test_must_empty_should_populated(self) -> None:
        query = _make_bool(must=[], should=[{"term": {"x": 1}}])
        assert has_clause(query) is True
