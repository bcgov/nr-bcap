from __future__ import annotations

import re

from pathlib import Path
from typing import TYPE_CHECKING

from models import CMFieldInfo, FieldInfo, VAL_QUALIFIERS

if TYPE_CHECKING:
    from collections.abc import Callable

    from playwright.sync_api import Page


JS_DIR = Path(__file__).resolve().parent / "js"


def _read_js(filename: str) -> str:
    content = (JS_DIR / filename).read_text(encoding="utf-8")
    return f"() => {{ {content} }}"


class SearchPage:
    def __init__(self, page: Page, base_url: str) -> None:
        self._base_url = base_url
        self._page = page

    def _dismiss_overlay(self) -> None:
        self._page.evaluate("() => window.__cm.dismiss_overlay()")

    def _retry_search(self) -> None:
        self._page.evaluate("() => window.__cm.retry_search()")

    def _run_and_wait_for_search(self, action: Callable[[], None]) -> None:
        for _ in range(3):
            response = None

            try:
                with self._page.expect_response(
                    lambda r: "/search/resources" in r.url,
                    timeout=120_000,
                ) as response_info:
                    action()

                response = response_info.value
            except Exception:
                print("Timed out waiting for /search/resources response")

            if response and response.status != 200:
                self._dismiss_overlay()
                self._page.wait_for_timeout(2000)
                self._retry_search()
                continue

            spinner = self._page.locator(".cross-model-loading-overlay")

            if spinner.count() > 0 and spinner.first.is_visible():
                try:
                    spinner.first.wait_for(state="hidden", timeout=120_000)
                except Exception:
                    self._dismiss_overlay()
                    self._page.wait_for_timeout(2000)
                    self._retry_search()
                    continue

            self._page.wait_for_timeout(1500)
            return

    def clear_filters(self) -> None:
        btn = self._page.locator("button.clear-filter")

        if btn.count() > 0 and btn.first.is_visible():
            btn.first.click()
            self._page.wait_for_timeout(1000)

    def click_tab(self, name: str) -> None:
        self._page.locator(
            "button.search-type-btn span[data-bind='text: filter.name']"
        ).filter(
            has_text=re.compile(f"^{re.escape(name)}$", re.IGNORECASE)
        ).first.click()
        self._page.wait_for_timeout(1500)

    def get_result_count(self) -> int:
        el = self._page.locator("p.search-title").first
        el.wait_for(timeout=30_000)

        for _ in range(10):
            text = el.inner_text()
            match = re.search(r"of\s*([\d,]+)", text)

            if match:
                return int(match.group(1).replace(",", ""))

            self._page.wait_for_timeout(500)

        return -1

    def navigate(self) -> None:
        self._page.goto(f"{self._base_url}/search", timeout=120_000)
        self._page.wait_for_load_state("networkidle", timeout=120_000)
        self._page.wait_for_timeout(3000)

    def wait_for_search_idle(self) -> None:
        self._page.wait_for_timeout(2000)
        spinner = self._page.locator(".cross-model-loading-overlay")

        if spinner.is_visible():
            spinner.wait_for(state="hidden", timeout=120_000)

        self._page.wait_for_load_state("networkidle")
        self._page.wait_for_timeout(3000)


class AdvancedSearchPage(SearchPage):
    def __init__(self, page: Page, base_url: str) -> None:
        super().__init__(page, base_url)
        self._injected = False

    def _drain_pending_responses(self) -> None:
        self._page.wait_for_load_state("networkidle")
        self._page.wait_for_timeout(500)

    def _inject(self) -> None:
        if not self._injected:
            self._page.evaluate(_read_js("advanced_search.js"))
            self._injected = True

    def add_card(self, graph: str, card: str) -> None:
        self._page.locator(f'div[aria-label="{graph} search facets"]').click()
        self._page.wait_for_timeout(500)

        try:
            with self._page.expect_response(
                lambda r: "/search/resources" in r.url and r.status == 200,
                timeout=15_000,
            ):
                self._page.locator(
                    f'a[aria-label="Add {card} for {graph} to search query"]'
                ).click()
        except Exception:
            self._page.locator(
                f'a[aria-label="Add {card} for {graph} to search query"]'
            ).click()

        self._page.wait_for_load_state("networkidle")
        self._page.wait_for_timeout(2000)
        self._inject()

    def get_testable_fields(self, testable_ops: set[str]) -> list[FieldInfo]:
        self._inject()
        raw = self._page.evaluate(
            "(ops) => window.__adv.get_testable_fields(ops)",
            list(testable_ops),
        )

        return [FieldInfo(**f) for f in raw]

    def navigate(self) -> None:
        super().navigate()
        self._injected = False

    def reset_and_wait(self, index: int) -> None:
        try:
            with self._page.expect_response(
                lambda r: "/search/resources" in r.url and r.status == 200,
                timeout=15_000,
            ):
                self.reset_qualifier(index)
        except Exception:
            self.reset_qualifier(index)
            self._page.wait_for_load_state("networkidle")
            self._page.wait_for_timeout(3000)

        self._page.wait_for_load_state("networkidle")
        self._page.wait_for_timeout(500)

    def reset_qualifier(self, index: int) -> None:
        self._inject()
        self._page.evaluate(
            "(i) => window.__adv.reset_qualifier(i)",
            index,
        )

    def set_and_wait(self, index: int, qualifier: str, text: str = "") -> None:
        self._drain_pending_responses()

        try:
            with self._page.expect_response(
                lambda r: "/search/resources" in r.url and r.status == 200,
                timeout=15_000,
            ):
                self.set_qualifier(index, qualifier, text)
        except Exception:
            self._page.wait_for_load_state("networkidle")
            self._page.wait_for_timeout(3000)

        self._page.wait_for_load_state("networkidle")
        self._page.wait_for_timeout(1000)

    def set_qualifier(self, index: int, qualifier: str, text: str = "") -> None:
        self._inject()
        self._page.evaluate(
            "([i, q, t]) => window.__adv.set_qualifier(i, q, t)",
            [index, qualifier, text],
        )


class CrossModelSearchPage(SearchPage):
    def __init__(self, page: Page, base_url: str) -> None:
        super().__init__(page, base_url)
        self._injected = False

    def _inject(self) -> None:
        if not self._injected:
            self._page.evaluate(_read_js("cross_model_search.js"))
            self._injected = True

    def add_card(self, graph_name: str, card_name: str) -> None:
        self._inject()
        self._page.evaluate(
            "(name) => window.__cm.click_graph(name)",
            graph_name,
        )
        self._page.wait_for_timeout(1000)

        self._page.evaluate(
            "(name) => window.__cm.click_card(name)",
            card_name,
        )
        self._page.wait_for_timeout(1500)

    def get_testable_fields(self, testable_ops: set[str]) -> list[CMFieldInfo]:
        self._inject()
        raw = self._page.evaluate(
            "(ops) => window.__cm.get_testable_fields(ops)",
            list(testable_ops),
        )

        return [CMFieldInfo(**f) for f in raw]

    def navigate(self) -> None:
        super().navigate()
        self._injected = False

    def set_filter(self, node_id: str, qualifier: str, text: str = "") -> None:
        self._inject()
        self._page.evaluate(
            "([n, q, t, v]) => window.__cm.set_filter(n, q, t, v)",
            [node_id, qualifier, text, qualifier in VAL_QUALIFIERS],
        )

    def set_filter_and_wait(self, node_id: str, qualifier: str, text: str = "") -> None:
        self._inject()
        self._run_and_wait_for_search(
            lambda: self.set_filter(node_id, qualifier, text),
        )

    def set_translate_target(self, slug: str) -> None:
        self._inject()
        self._page.evaluate(
            "(s) => window.__cm.set_translate_target(s)",
            slug,
        )
        self._page.wait_for_timeout(1000)

    def swap_filter(
        self,
        prev_node_id: str,
        next_node_id: str,
        next_qualifier: str,
        next_text: str = "",
    ) -> None:
        self._inject()
        self._page.evaluate(
            "([n, q, t, v]) => window.__cm.set_filter(n, q, t, v)",
            [next_node_id, next_qualifier, next_text, next_qualifier in VAL_QUALIFIERS],
        )
        self._page.evaluate(
            "(n) => window.__cm.deactivate_filter(n)",
            prev_node_id,
        )

    def swap_filter_and_wait(
        self,
        prev_node_id: str,
        next_node_id: str,
        next_qualifier: str,
        next_text: str = "",
    ) -> None:
        self._inject()
        self._run_and_wait_for_search(
            lambda: self.swap_filter(prev_node_id, next_node_id, next_qualifier, next_text),
        )
