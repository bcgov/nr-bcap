from __future__ import annotations

import pytest
from typing_extensions import Any

from bcap.search_components.cross_model_advanced_search import chunk


class TestChunk:
    @pytest.mark.parametrize(
        "items,size,expected",
        [
            ([], 10, []),
            ([1, 2, 3, 4], 2, [[1, 2], [3, 4]]),
            ([1, 2, 3, 4, 5], 2, [[1, 2], [3, 4], [5]]),
            ([1, 2], 10, [[1, 2]]),
            ([1, 2, 3], 3, [[1, 2, 3]]),
            ([1, 2, 3], 1, [[1], [2], [3]]),
            (["a", "b", "c", "d"], 2, [["a", "b"], ["c", "d"]]),
            ([1, "a", None, True, 3.14], 2, [[1, "a"], [None, True], [3.14]]),
        ],
    )
    def test_chunk(self, items: list[Any], size: int, expected: list[list]) -> None:
        assert list(chunk(items, size)) == expected

    def test_is_lazy(self) -> None:
        gen = chunk(list(range(100)), 10)
        assert next(gen) == list(range(10))
