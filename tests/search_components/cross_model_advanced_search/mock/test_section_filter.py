from __future__ import annotations

from unittest.mock import MagicMock, patch

from bcap.search_components.cross_model_advanced_search import (
    Logic,
    SectionFilter,
)
from helper import _make_bool, _uuid


class TestSectionFilterBuild:
    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_no_groups(self, mock_bool_cls: MagicMock) -> None:
        mock_query = _make_bool()
        mock_bool_cls.return_value = mock_query
        sf = SectionFilter(graph=_uuid(), groups=[])
        result = sf.build(MagicMock(), {}, MagicMock())
        assert result == mock_query

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_single_group(self, mock_bool_cls: MagicMock) -> None:
        mock_query = _make_bool()
        mock_bool_cls.return_value = mock_query

        group = MagicMock()
        group_query = _make_bool(must=[{"term": {"x": "y"}}])
        group.build.return_value = group_query
        group.operator = Logic.AND

        sf = SectionFilter(graph=_uuid(), groups=[group])
        sf.build(MagicMock(), {}, MagicMock())
        mock_query.must.assert_called_once_with(group_query)

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_all_and_operators(self, mock_bool_cls: MagicMock) -> None:
        mock_query = _make_bool()
        mock_bool_cls.return_value = mock_query

        groups: list[MagicMock] = []
        for _ in range(3):
            group = MagicMock()
            gq = _make_bool(must=[{"term": {"x": "y"}}])
            group.build.return_value = gq
            group.operator = Logic.AND
            groups.append(group)

        sf = SectionFilter(graph=_uuid(), groups=groups)
        sf.build(MagicMock(), {}, MagicMock())
        assert mock_query.must.call_count == 3

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_all_or_operators(self, mock_bool_cls: MagicMock) -> None:
        mock_query = _make_bool()
        mock_bool_cls.return_value = mock_query

        groups: list[MagicMock] = []
        for _ in range(3):
            group = MagicMock()
            gq = _make_bool(must=[{"term": {"x": "y"}}])
            group.build.return_value = gq
            group.operator = Logic.OR
            groups.append(group)

        sf = SectionFilter(graph=_uuid(), groups=groups)
        sf.build(MagicMock(), {}, MagicMock())
        assert mock_query.should.call_count == 3
        assert mock_query.dsl["bool"]["minimum_should_match"] == 1

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_mixed_operators(self, mock_bool_cls: MagicMock) -> None:
        """AND, OR mixed: groups 0+1 are AND'd, then OR'd with group 2."""
        bool_instances: list[MagicMock] = []

        def make_bool() -> MagicMock:
            b = _make_bool()
            bool_instances.append(b)
            return b

        mock_bool_cls.side_effect = make_bool

        g0 = MagicMock()
        g0.build.return_value = _make_bool(must=[{"x": 1}])
        g0.operator = Logic.AND

        g1 = MagicMock()
        g1.build.return_value = _make_bool(must=[{"x": 2}])
        g1.operator = Logic.OR

        g2 = MagicMock()
        g2.build.return_value = _make_bool(must=[{"x": 3}])
        g2.operator = Logic.AND

        sf = SectionFilter(graph=_uuid(), groups=[g0, g1, g2])
        result = sf.build(MagicMock(), {}, MagicMock())
        assert result.dsl["bool"]["minimum_should_match"] == 1

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_skips_empty_groups(self, mock_bool_cls: MagicMock) -> None:
        mock_query = _make_bool()
        mock_bool_cls.return_value = mock_query

        empty_group = MagicMock()
        empty_group.build.return_value = _make_bool()
        empty_group.operator = Logic.AND

        valid_group = MagicMock()
        valid_group.build.return_value = _make_bool(must=[{"term": {"x": "y"}}])
        valid_group.operator = Logic.AND

        sf = SectionFilter(graph=_uuid(), groups=[empty_group, valid_group])
        sf.build(MagicMock(), {}, MagicMock())
        mock_query.must.assert_called_once()

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_all_groups_empty_produces_empty_query(
        self, mock_bool_cls: MagicMock
    ) -> None:
        mock_query = _make_bool()
        mock_bool_cls.return_value = mock_query

        groups: list[MagicMock] = []
        for _ in range(3):
            g = MagicMock()
            g.build.return_value = _make_bool()
            g.operator = Logic.AND
            groups.append(g)

        sf = SectionFilter(graph=_uuid(), groups=groups)
        sf.build(MagicMock(), {}, MagicMock())
        mock_query.must.assert_not_called()
        mock_query.should.assert_not_called()

    @patch("bcap.search_components.cross_model_advanced_search.Bool")
    def test_or_after_and_group(self, mock_bool_cls: MagicMock) -> None:
        mock_query = _make_bool()
        mock_bool_cls.return_value = mock_query

        and_group = MagicMock()
        and_group.build.return_value = _make_bool(must=[{"term": {"a": "1"}}])
        and_group.operator = Logic.AND

        or_group = MagicMock()
        or_group.build.return_value = _make_bool(must=[{"term": {"b": "2"}}])
        or_group.operator = Logic.OR

        sf = SectionFilter(graph=_uuid(), groups=[and_group, or_group])
        sf.build(MagicMock(), {}, MagicMock())
