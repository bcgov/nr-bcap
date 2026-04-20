from __future__ import annotations

from unittest.mock import MagicMock, patch

from typing_extensions import Any

from bcap.search_components.cross_model_advanced_search import (
    GroupFilter,
    Logic,
    MatchType,
)
from helper import _make_bool


class TestGroupFilterBuild:
    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.Nested")
    def test_empty_cards(
        self, mock_nested_cls: MagicMock, mock_bool_cls: MagicMock
    ) -> None:
        mock_query = _make_bool()
        mock_bool_cls.return_value = mock_query
        gf = GroupFilter(cards=[], match_type=MatchType.ALL, operator=Logic.AND)
        factory = MagicMock()
        nodes: dict[str, Any] = {}
        request = MagicMock()
        _ = gf.build(factory, nodes, request)
        mock_nested_cls.assert_not_called()

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.Nested")
    def test_match_all_uses_must(
        self, mock_nested_cls: MagicMock, mock_bool_cls: MagicMock
    ) -> None:
        mock_query = _make_bool()
        mock_bool_cls.return_value = mock_query

        card = MagicMock()
        card_query = _make_bool(must=[{"term": {"x": "y"}}])
        null_query = _make_bool()
        negation_query = _make_bool()
        card.build.return_value = (card_query, negation_query, null_query)

        gf = GroupFilter(cards=[card], match_type=MatchType.ALL, operator=Logic.AND)
        factory = MagicMock()
        nodes: dict[str, Any] = {}
        request = MagicMock()
        gf.build(factory, nodes, request)
        mock_query.must.assert_called_once()

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.Nested")
    def test_match_any_uses_should(
        self, mock_nested_cls: MagicMock, mock_bool_cls: MagicMock
    ) -> None:
        mock_query = _make_bool()
        mock_bool_cls.return_value = mock_query

        card = MagicMock()
        card_query = _make_bool(must=[{"term": {"x": "y"}}])
        null_query = _make_bool()
        negation_query = _make_bool()
        card.build.return_value = (card_query, negation_query, null_query)

        gf = GroupFilter(cards=[card], match_type=MatchType.ANY, operator=Logic.AND)
        factory = MagicMock()
        nodes: dict[str, Any] = {}
        request = MagicMock()
        gf.build(factory, nodes, request)
        mock_query.should.assert_called_once()

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.Nested")
    def test_match_any_sets_minimum_should_match(
        self, mock_nested_cls: MagicMock, mock_bool_cls: MagicMock
    ) -> None:
        mock_query = _make_bool(should=[{"nested": {}}])
        mock_bool_cls.return_value = mock_query

        card = MagicMock()
        card_query = _make_bool(must=[{"term": {"x": "y"}}])
        null_query = _make_bool()
        negation_query = _make_bool()
        card.build.return_value = (card_query, negation_query, null_query)

        gf = GroupFilter(cards=[card], match_type=MatchType.ANY, operator=Logic.AND)
        factory = MagicMock()
        nodes: dict[str, Any] = {}
        request = MagicMock()
        result = gf.build(factory, nodes, request)
        assert result.dsl["bool"]["minimum_should_match"] == 1

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.Nested")
    def test_skips_card_with_no_clauses(
        self, mock_nested_cls: MagicMock, mock_bool_cls: MagicMock
    ) -> None:
        mock_query = _make_bool()
        mock_bool_cls.return_value = mock_query

        card = MagicMock()
        card.build.return_value = (_make_bool(), _make_bool(), _make_bool())

        gf = GroupFilter(cards=[card], match_type=MatchType.ALL, operator=Logic.AND)
        factory = MagicMock()
        nodes: dict[str, Any] = {}
        request = MagicMock()
        gf.build(factory, nodes, request)
        mock_query.must.assert_not_called()
        mock_query.should.assert_not_called()

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_null_query_with_clauses_added_as_must(
        self, mock_bool_cls: MagicMock
    ) -> None:
        mock_query = _make_bool()
        mock_bool_cls.return_value = mock_query

        card = MagicMock()
        card_query = _make_bool()
        null_query = _make_bool(must=[{"exists": {"field": "tiles.data.node-1"}}])
        negation_query = _make_bool()
        card.build.return_value = (card_query, negation_query, null_query)

        gf = GroupFilter(cards=[card], match_type=MatchType.ALL, operator=Logic.AND)
        factory = MagicMock()
        nodes: dict[str, Any] = {}
        request = MagicMock()
        gf.build(factory, nodes, request)
        mock_query.must.assert_called_once_with(null_query)

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_null_query_match_any_uses_should(self, mock_bool_cls: MagicMock) -> None:
        mock_query = _make_bool()
        mock_bool_cls.return_value = mock_query

        card = MagicMock()
        card_query = _make_bool()
        null_query = _make_bool(must=[{"exists": {"field": "tiles.data.node-1"}}])
        negation_query = _make_bool()
        card.build.return_value = (card_query, negation_query, null_query)

        gf = GroupFilter(cards=[card], match_type=MatchType.ANY, operator=Logic.AND)
        factory = MagicMock()
        nodes: dict[str, Any] = {}
        request = MagicMock()
        gf.build(factory, nodes, request)
        mock_query.should.assert_called_once_with(null_query)

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    @patch("bcap.search_components.cross_model_advanced_search.Nested")
    def test_multiple_cards(
        self, mock_nested_cls: MagicMock, mock_bool_cls: MagicMock
    ) -> None:
        mock_query = _make_bool()
        mock_bool_cls.return_value = mock_query

        cards: list[MagicMock] = []
        for _ in range(3):
            card = MagicMock()
            card_query = _make_bool(must=[{"term": {"x": "y"}}])
            null_query = _make_bool()
            negation_query = _make_bool()
            card.build.return_value = (card_query, negation_query, null_query)
            cards.append(card)

        gf = GroupFilter(cards=cards, match_type=MatchType.ALL, operator=Logic.AND)
        factory = MagicMock()
        nodes: dict[str, Any] = {}
        request = MagicMock()
        gf.build(factory, nodes, request)
        assert mock_query.must.call_count == 3
