from __future__ import annotations

import pytest

from bcap.search_components.cross_model_advanced_search import (
    Logic,
    MatchType,
    TranslateMode,
)


class TestEnums:
    @pytest.mark.parametrize(
        "member,value",
        [
            pytest.param(Logic.AND, "and", id="logic_and"),
            pytest.param(Logic.OR, "or", id="logic_or"),
            pytest.param(MatchType.ALL, "all", id="match_type_all"),
            pytest.param(MatchType.ANY, "any", id="match_type_any"),
            pytest.param(TranslateMode.NONE, "none", id="translate_mode_none"),
        ],
    )
    def test_members_are_strings_that_round_trip(self, member, value: str) -> None:
        assert member == value
        assert isinstance(member, str)
        assert type(member)(value) is member
