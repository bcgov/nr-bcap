from __future__ import annotations

from unittest.mock import MagicMock

from typing_extensions import Any

from bcap.search_components.cross_model_advanced_search import Scroller
from helper import _uuid


class TestScrollerIds:
    def test_empty_result(self) -> None:
        engine = MagicMock()
        engine.search.return_value = {
            "hits": {"total": {"value": 0}},
        }

        scroller = Scroller(engine)
        result: set[str] = scroller.ids({"bool": {}})
        assert result == set()

    def test_small_result_set(self) -> None:
        rid1 = _uuid()
        rid2 = _uuid()

        engine = MagicMock()
        engine.search.side_effect = [
            {"hits": {"total": {"value": 2}}},
            {"hits": {"hits": [{"_id": rid1}, {"_id": rid2}]}},
        ]

        scroller = Scroller(engine)
        result: set[str] = scroller.ids({"bool": {}})
        assert result == {rid1, rid2}

    def test_large_result_set_uses_composite(self) -> None:
        rids = [_uuid() for _ in range(3)]

        engine = MagicMock()
        engine.search.side_effect = [
            {"hits": {"total": {"value": 15000}}},
            {
                "aggregations": {
                    "ids": {
                        "buckets": [{"key": {"rid": rid}} for rid in rids[:2]],
                        "after_key": {"rid": rids[1]},
                    }
                }
            },
            {
                "aggregations": {
                    "ids": {
                        "buckets": [{"key": {"rid": rids[2]}}],
                    }
                }
            },
        ]

        scroller = Scroller(engine)
        result: set[str] = scroller.ids({"bool": {}})
        assert result == set(rids)

    def test_composite_no_after_key_stops(self) -> None:
        rid = _uuid()
        engine = MagicMock()
        engine.search.side_effect = [
            {"hits": {"total": {"value": 15000}}},
            {
                "aggregations": {
                    "ids": {
                        "buckets": [{"key": {"rid": rid}}],
                    }
                }
            },
        ]

        scroller = Scroller(engine)
        result: set[str] = scroller.ids({"bool": {}})
        assert result == {rid}

    def test_composite_empty_buckets_stops(self) -> None:
        engine = MagicMock()
        engine.search.side_effect = [
            {"hits": {"total": {"value": 15000}}},
            {"aggregations": {"ids": {"buckets": []}}},
        ]

        scroller = Scroller(engine)
        result: set[str] = scroller.ids({"bool": {}})
        assert result == set()

    def test_exactly_10000_uses_simple_query(self) -> None:
        rids = [_uuid() for _ in range(3)]
        engine = MagicMock()
        engine.search.side_effect = [
            {"hits": {"total": {"value": 10000}}},
            {"hits": {"hits": [{"_id": rid} for rid in rids]}},
        ]

        scroller = Scroller(engine)
        result: set[str] = scroller.ids({"bool": {}})
        assert result == set(rids)
        assert engine.search.call_count == 2

    def test_10001_uses_composite(self) -> None:
        rid = _uuid()
        engine = MagicMock()
        engine.search.side_effect = [
            {"hits": {"total": {"value": 10001}}},
            {
                "aggregations": {
                    "ids": {
                        "buckets": [{"key": {"rid": rid}}],
                    }
                }
            },
        ]

        scroller = Scroller(engine)
        result: set[str] = scroller.ids({"bool": {}})
        assert result == {rid}

    def test_small_result_passes_source_false(self) -> None:
        engine = MagicMock()
        engine.search.side_effect = [
            {"hits": {"total": {"value": 1}}},
            {"hits": {"hits": [{"_id": _uuid()}]}},
        ]

        scroller = Scroller(engine)
        scroller.ids({"bool": {}})

        second_call = engine.search.call_args_list[1]
        assert second_call.kwargs.get("_source") is False

    def test_composite_passes_size_zero(self) -> None:
        engine = MagicMock()
        engine.search.side_effect = [
            {"hits": {"total": {"value": 15000}}},
            {"aggregations": {"ids": {"buckets": []}}},
        ]

        scroller = Scroller(engine)
        scroller.ids({"bool": {}})

        second_call = engine.search.call_args_list[1]
        assert second_call.kwargs.get("size") == 0

    def test_composite_multiple_pages(self) -> None:
        page1_rids = [_uuid() for _ in range(3)]
        page2_rids = [_uuid() for _ in range(3)]
        page3_rids = [_uuid() for _ in range(2)]

        engine = MagicMock()
        engine.search.side_effect = [
            {"hits": {"total": {"value": 50000}}},
            {
                "aggregations": {
                    "ids": {
                        "buckets": [{"key": {"rid": rid}} for rid in page1_rids],
                        "after_key": {"rid": page1_rids[-1]},
                    }
                }
            },
            {
                "aggregations": {
                    "ids": {
                        "buckets": [{"key": {"rid": rid}} for rid in page2_rids],
                        "after_key": {"rid": page2_rids[-1]},
                    }
                }
            },
            {
                "aggregations": {
                    "ids": {
                        "buckets": [{"key": {"rid": rid}} for rid in page3_rids],
                    }
                }
            },
        ]

        scroller = Scroller(engine)
        result: set[str] = scroller.ids({"bool": {}})
        assert result == set(page1_rids + page2_rids + page3_rids)

    def test_single_hit(self) -> None:
        rid = _uuid()
        engine = MagicMock()
        engine.search.side_effect = [
            {"hits": {"total": {"value": 1}}},
            {"hits": {"hits": [{"_id": rid}]}},
        ]

        scroller = Scroller(engine)
        result: set[str] = scroller.ids({"bool": {}})
        assert result == {rid}

    def test_count_response_missing_total_key(self) -> None:
        engine = MagicMock()
        engine.search.return_value = {"hits": {}}

        scroller = Scroller(engine)
        result: set[str] = scroller.ids({"bool": {}})
        assert result == set()

    def test_count_response_missing_hits_key(self) -> None:
        engine = MagicMock()
        engine.search.return_value = {}

        scroller = Scroller(engine)
        result: set[str] = scroller.ids({"bool": {}})
        assert result == set()

    def test_simple_query_empty_hits_list(self) -> None:
        engine = MagicMock()
        engine.search.side_effect = [
            {"hits": {"total": {"value": 5}}},
            {"hits": {"hits": []}},
        ]

        scroller = Scroller(engine)
        result: set[str] = scroller.ids({"bool": {}})
        assert result == set()

    def test_composite_missing_aggregations_key(self) -> None:
        engine = MagicMock()
        engine.search.side_effect = [
            {"hits": {"total": {"value": 20000}}},
            {},
        ]

        scroller = Scroller(engine)
        result: set[str] = scroller.ids({"bool": {}})
        assert result == set()

    def test_composite_missing_ids_key(self) -> None:
        engine = MagicMock()
        engine.search.side_effect = [
            {"hits": {"total": {"value": 20000}}},
            {"aggregations": {}},
        ]

        scroller = Scroller(engine)
        result: set[str] = scroller.ids({"bool": {}})
        assert result == set()

    def test_composite_preserves_after_key_between_pages(self) -> None:
        after_key_val = {"rid": "marker-id"}
        engine = MagicMock()
        engine.search.side_effect = [
            {"hits": {"total": {"value": 25000}}},
            {
                "aggregations": {
                    "ids": {
                        "buckets": [{"key": {"rid": _uuid()}}],
                        "after_key": after_key_val,
                    }
                }
            },
            {
                "aggregations": {
                    "ids": {
                        "buckets": [],
                    }
                }
            },
        ]

        scroller = Scroller(engine)
        scroller.ids({"bool": {}})

        third_call = engine.search.call_args_list[2]
        aggs = third_call.kwargs.get("aggs", {})
        assert aggs["ids"]["composite"]["after"] == after_key_val

    def test_duplicate_ids_across_composite_pages_deduplicated(self) -> None:
        shared_rid = _uuid()
        engine = MagicMock()
        engine.search.side_effect = [
            {"hits": {"total": {"value": 20000}}},
            {
                "aggregations": {
                    "ids": {
                        "buckets": [{"key": {"rid": shared_rid}}],
                        "after_key": {"rid": shared_rid},
                    }
                }
            },
            {
                "aggregations": {
                    "ids": {
                        "buckets": [{"key": {"rid": shared_rid}}],
                    }
                }
            },
        ]

        scroller = Scroller(engine)
        result: set[str] = scroller.ids({"bool": {}})
        assert result == {shared_rid}

    def test_simple_query_passes_total_as_size(self) -> None:
        engine = MagicMock()
        engine.search.side_effect = [
            {"hits": {"total": {"value": 42}}},
            {"hits": {"hits": []}},
        ]

        scroller = Scroller(engine)
        scroller.ids({"bool": {}})

        second_call = engine.search.call_args_list[1]
        assert second_call.kwargs.get("size") == 42

    def test_count_call_uses_size_zero_and_track_total(self) -> None:
        engine = MagicMock()
        engine.search.return_value = {"hits": {"total": {"value": 0}}}

        scroller = Scroller(engine)
        scroller.ids({"bool": {"must": []}})

        first_call = engine.search.call_args_list[0]
        assert first_call.kwargs.get("size") == 0
        assert first_call.kwargs.get("track_total_hits") is True
