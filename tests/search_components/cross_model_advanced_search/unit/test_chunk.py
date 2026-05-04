from __future__ import annotations

from bcap.search_components.cross_model_advanced_search import chunk


class TestChunk:
    def test_empty_list(self) -> None:
        assert list(chunk([], 10)) == []

    def test_exact_multiple(self) -> None:
        result: list[list[int]] = list(chunk([1, 2, 3, 4], 2))
        assert result == [[1, 2], [3, 4]]

    def test_remainder(self) -> None:
        result: list[list[int]] = list(chunk([1, 2, 3, 4, 5], 2))
        assert result == [[1, 2], [3, 4], [5]]

    def test_size_larger_than_list(self) -> None:
        result: list[list[int]] = list(chunk([1, 2], 10))
        assert result == [[1, 2]]

    def test_single_element_chunks(self) -> None:
        result: list[list[int]] = list(chunk([1, 2, 3], 1))
        assert result == [[1], [2], [3]]

    def test_single_element_list(self) -> None:
        result: list[list[int]] = list(chunk([42], 5))
        assert result == [[42]]

    def test_size_equals_length(self) -> None:
        result: list[list[int]] = list(chunk([1, 2, 3], 3))
        assert result == [[1, 2, 3]]

    def test_string_items(self) -> None:
        result: list[list[str]] = list(chunk(["a", "b", "c", "d"], 2))
        assert result == [["a", "b"], ["c", "d"]]

    def test_returns_generator(self) -> None:
        gen = chunk([1, 2, 3], 2)
        assert hasattr(gen, "__next__")

    def test_large_list_small_chunks(self) -> None:
        items = list(range(1000))
        result: list[list[int]] = list(chunk(items, 100))
        assert len(result) == 10
        assert all(len(c) == 100 for c in result)

    def test_large_list_single_chunk(self) -> None:
        items = list(range(1000))
        result: list[list[int]] = list(chunk(items, 1000))
        assert len(result) == 1
        assert result[0] == items

    def test_lazy_evaluation(self) -> None:
        gen = chunk(list(range(100)), 10)
        first = next(gen)
        assert first == list(range(10))

    def test_mixed_types(self) -> None:
        items = [1, "a", None, True, 3.14]
        result = list(chunk(items, 2))
        assert result == [[1, "a"], [None, True], [3.14]]

    def test_chunk_preserves_order(self) -> None:
        items = list(range(7))
        result: list[list[int]] = list(chunk(items, 3))
        flattened = [item for sublist in result for item in sublist]
        assert flattened == items

    def test_two_elements_size_two(self) -> None:
        result: list[list[int]] = list(chunk([1, 2], 2))
        assert result == [[1, 2]]

    def test_three_elements_size_two(self) -> None:
        result: list[list[int]] = list(chunk([1, 2, 3], 2))
        assert result == [[1, 2], [3]]
