from __future__ import annotations

from bcap.search_components.cross_model_advanced_search import (
    Logic,
    MatchType,
    TranslateMode,
)


class TestEnums:
    def test_logic_values(self) -> None:
        assert Logic.AND == "and"
        assert Logic.OR == "or"

    def test_match_type_values(self) -> None:
        assert MatchType.ALL == "all"
        assert MatchType.ANY == "any"

    def test_translate_mode_values(self) -> None:
        assert TranslateMode.NONE == "none"

    def test_logic_is_str(self) -> None:
        assert isinstance(Logic.AND, str)
        assert isinstance(Logic.OR, str)

    def test_match_type_is_str(self) -> None:
        assert isinstance(MatchType.ALL, str)
        assert isinstance(MatchType.ANY, str)

    def test_translate_mode_is_str(self) -> None:
        assert isinstance(TranslateMode.NONE, str)

    def test_logic_from_value(self) -> None:
        assert Logic("and") == Logic.AND
        assert Logic("or") == Logic.OR

    def test_match_type_from_value(self) -> None:
        assert MatchType("all") == MatchType.ALL
        assert MatchType("any") == MatchType.ANY

    def test_translate_mode_from_value(self) -> None:
        assert TranslateMode("none") == TranslateMode.NONE
