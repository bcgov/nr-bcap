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
            (Logic.AND, "and"),
            (Logic.OR, "or"),
            (MatchType.ALL, "all"),
            (MatchType.ANY, "any"),
            (TranslateMode.NONE, "none"),
        ],
    )
    def test_members_are_strings_that_round_trip(self, member, value: str) -> None:
        assert member == value
        assert isinstance(member, str)
        assert type(member)(value) is member
