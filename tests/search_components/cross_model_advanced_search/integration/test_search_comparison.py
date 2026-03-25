from __future__ import annotations

import pytest

from adv_cache import AdvancedSearchCache
from db import get_inventory, get_sample_value
from inv_cache import InventoryCache
from models import CardInfo, Mismatch, QualifierTestItem, get_qualifiers_for, qualifier_needs_value
from pages import AdvancedSearchPage, CrossModelSearchPage
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page


_adv_cache = AdvancedSearchCache()
_inv_cache = InventoryCache()
_INVENTORY = _inv_cache.get()

if _INVENTORY is None:
    _INVENTORY = get_inventory()
    _inv_cache.put(_INVENTORY)


def _fetch_adv_counts(
    adv: AdvancedSearchPage,
    graph: str,
    card: str,
    card_info: CardInfo,
) -> dict:
    all_ops = set()

    for node in card_info.nodes:
        all_ops |= get_qualifiers_for(node.datatype)

    adv.navigate()
    adv.click_tab("Advanced")
    adv.add_card(graph, card)

    fields = adv.get_testable_fields(all_ops)
    node_lookup = card_info.node_lookup
    counts = {}

    for field in fields:
        field_counts = {}
        node_info = node_lookup.get(field.label)
        datatype = node_info.datatype if node_info else "string"
        allowed_ops = get_qualifiers_for(datatype)

        for qualifier in field.qualifiers:
            if qualifier not in allowed_ops:
                continue

            text = ""

            if qualifier_needs_value(qualifier, datatype) and node_info:
                text = get_sample_value(node_info.node_id, datatype) or ""

                if not text:
                    continue

            cache_key = f"{qualifier}:{text}" if text else qualifier
            adv.set_and_wait(field.index, qualifier, text)
            field_counts[cache_key] = adv.get_result_count()
            adv.reset_and_wait(field.index)

        if field_counts:
            counts[field.label] = field_counts

    return counts


def _build_test_items(
    adv_counts: dict,
    cm_fields: list,
) -> list[QualifierTestItem]:
    cm_lookup = {f.label: f for f in cm_fields}
    items = []

    for label, qualifier_counts in adv_counts.items():
        if label not in cm_lookup:
            continue

        cm_field = cm_lookup[label]

        for cache_key in qualifier_counts:
            item = QualifierTestItem.from_cache_key(label, cm_field.node_id, cache_key)

            if item.qualifier in cm_field.qualifiers:
                items.append(item)

    return items


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "card_info" not in metafunc.fixturenames:
        return

    if not _INVENTORY:
        metafunc.parametrize(
            "card_info",
            [pytest.param(
                None,
                marks=pytest.mark.skip(reason="No inventory (Django not available)"),
            )],
            ids=["no_inventory"],
        )
        return

    cards = [CardInfo.from_dict(c) for c in _INVENTORY]

    metafunc.parametrize(
        "card_info",
        cards,
        ids=[c.test_id for c in cards],
    )


class TestCardComparison:
    def test_qualifier_counts(
        self,
        card_info: CardInfo,
        page: Page,
        base_url: str,
    ) -> None:
        graph = card_info.graph_name
        card = card_info.card_name
        adv = AdvancedSearchPage(page, base_url)
        cm = CrossModelSearchPage(page, base_url)

        # Fetch or load cached Advanced Search counts
        adv_counts = _adv_cache.get(graph, card)

        if adv_counts is None:
            print(f"\n  Caching Advanced Search counts for {graph} / {card}...")
            adv_counts = _fetch_adv_counts(adv, graph, card, card_info)
            _adv_cache.put(graph, card, adv_counts)
            total_q = sum(len(v) for v in adv_counts.values())
            print(f"  Cached {total_q} qualifier counts across {len(adv_counts)} fields")
        else:
            print(f"\n  Using cached Advanced Search counts for {graph} / {card}")

        if not adv_counts:
            pytest.skip(f"No testable fields found for {graph} / {card}")

        # Set up cross-model search
        all_ops = set()

        for node in card_info.nodes:
            all_ops |= get_qualifiers_for(node.datatype)

        cm.navigate()
        cm.click_tab("Cross-Model Advanced Search")
        cm.add_card(graph, card)
        cm.set_translate_target(card_info.slug)

        cm_fields = cm.get_testable_fields(all_ops)

        if not cm_fields:
            pytest.skip(f"No testable CM fields for {graph} / {card}")

        test_items = _build_test_items(adv_counts, cm_fields)

        if not test_items:
            pytest.skip(f"No overlapping fields for {graph} / {card}")

        print(f"  Testing {len(test_items)} qualifier(s) via KO swap...")

        # Iterate using KO swap (no page reloads)
        mismatches = []

        for idx, item in enumerate(test_items):
            if idx == 0:
                cm.set_filter_and_wait(item.node_id, item.qualifier, item.text)

            cm_count = cm.get_result_count()
            adv_count = adv_counts[item.label][item.cache_key]
            match = cm_count == adv_count
            status = "OK" if match else "MISMATCH"
            print(
                f"  [{idx + 1}/{len(test_items)}] {item.display}: "
                f"Adv={adv_count}, CM={cm_count} -> {status}"
            )

            if not match:
                mismatches.append(Mismatch(
                    adv_count=adv_count,
                    cm_count=cm_count,
                    display=item.display,
                ))

            # Transition to next item
            if idx < len(test_items) - 1:
                next_item = test_items[idx + 1]

                if next_item.node_id == item.node_id:
                    cm.set_filter_and_wait(item.node_id, next_item.qualifier, next_item.text)
                else:
                    cm.swap_filter_and_wait(
                        item.node_id,
                        next_item.node_id,
                        next_item.qualifier,
                        next_item.text,
                    )

        assert not mismatches, (
            f"[{graph} / {card}] qualifier mismatches:\n"
            + "\n".join(f"  - {m}" for m in mismatches)
        )


class TestBaselineComparison:
    def test_unfiltered_totals_match(
        self,
        page: Page,
        base_url: str,
    ) -> None:
        search = AdvancedSearchPage(page, base_url)

        search.navigate()
        search.click_tab("Advanced")
        search.clear_filters()
        search.wait_for_search_idle()
        adv_count = search.get_result_count()

        search.clear_filters()
        search.click_tab("Cross-Model Advanced Search")
        search.wait_for_search_idle()
        cm_count = search.get_result_count()

        assert adv_count == cm_count, (
            f"Unfiltered mismatch: Advanced={adv_count}, Cross-Model={cm_count}"
        )
