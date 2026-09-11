from __future__ import annotations

import pytest
from typing_extensions import Any

from bcap.search_components.cross_model_advanced_search import chunk


class TestChunk:
    @pytest.mark.parametrize(
        "items,size,expected",
        [
            pytest.param([], 10, [], id="empty_list"),
            pytest.param([1, 2, 3, 4], 2, [[1, 2], [3, 4]], id="exact_multiple"),
            pytest.param([1, 2, 3, 4, 5], 2, [[1, 2], [3, 4], [5]], id="remainder"),
            pytest.param([1, 2], 10, [[1, 2]], id="size_larger_than_list"),
            pytest.param([1, 2, 3], 3, [[1, 2, 3]], id="size_equals_length"),
            pytest.param([1, 2, 3], 1, [[1], [2], [3]], id="single_element_chunks"),
            pytest.param(
                ["a", "b", "c", "d"],
                2,
                [["a", "b"], ["c", "d"]],
                id="string_items",
            ),
            pytest.param(
                [1, "a", None, True, 3.14],
                2,
                [[1, "a"], [None, True], [3.14]],
                id="mixed_types",
            ),
        ],
    )
    def test_chunk(self, items: list[Any], size: int, expected: list[list]) -> None:
        assert list(chunk(items, size)) == expected

    def test_is_lazy(self) -> None:
        gen = chunk(list(range(100)), 10)
        assert next(gen) == list(range(10))
