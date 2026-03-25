from __future__ import annotations

import json
import logging
import os
import socket
import sys
import threading
import urllib.request

from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Browser, BrowserContext, Page, Playwright


logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent / ".cache"
_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


def _load_env() -> None:
    if not _ENV_FILE.exists():
        return

    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("\"'")

        if key and key not in os.environ:
            os.environ[key] = value


_load_env()

IN_DOCKER = Path("/.dockerenv").exists()
CDP_ENDPOINT = os.environ.get("BCAP_CDP", "")

_DEFAULT_URL = "http://localhost:80/bcap" if IN_DOCKER else "http://localhost:82/bcap"
BASE_URL = os.environ.get("BCAP_BASE_URL", _DEFAULT_URL)


def _clear_caches() -> None:
    for f in CACHE_DIR.glob("*.json"):
        f.unlink(missing_ok=True)


def _forward_connection(src: socket.socket) -> None:
    dst = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        dst.connect(("127.0.0.1", 80))
    except Exception:
        src.close()
        return

    def _relay(a: socket.socket, b: socket.socket) -> None:
        try:
            while True:
                data = a.recv(65536)

                if not data:
                    break

                b.sendall(data)
        except Exception:
            pass

        a.close()
        b.close()

    threading.Thread(target=_relay, args=(src, dst), daemon=True).start()
    threading.Thread(target=_relay, args=(dst, src), daemon=True).start()


class _PortForwarder:
    def __init__(self, listen_port: int) -> None:
        self._listen_port = listen_port
        self._server: socket.socket | None = None

    def start(self) -> None:
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", self._listen_port))
        self._server.listen(5)
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def stop(self) -> None:
        if self._server:
            self._server.close()
            self._server = None

    def _accept_loop(self) -> None:
        while self._server:
            try:
                client, _ = self._server.accept()
                _forward_connection(client)
            except Exception:
                break


def _do_idir_login(page: Page) -> None:
    username = os.environ.get("BCAP_IDIR_USER", "")
    password = os.environ.get("BCAP_IDIR_PASSWORD", "")

    if not username or not password:
        pytest.exit(
            "No credentials provided. Set BCAP_IDIR_USER and BCAP_IDIR_PASSWORD.",
            returncode=1,
        )

    forwarder = _PortForwarder(82) if IN_DOCKER else None

    if forwarder:
        forwarder.start()

    print("\n  [auth] Loading splash page...")
    page.goto(f"{BASE_URL}/", timeout=60_000)
    page.wait_for_load_state("networkidle", timeout=60_000)

    print("  [auth] Clicking log in...")
    page.get_by_role("link", name="log in").or_(
        page.get_by_role("button", name="log in")
    ).first.click()

    print("  [auth] Clicking IDIR...")
    page.locator("#social-idir").click()

    print("  [auth] Waiting for IDIR form...")
    page.wait_for_url("**/logon.cgi**", timeout=60_000)
    page.wait_for_load_state("networkidle", timeout=30_000)

    print("  [auth] Filling credentials...")
    page.fill('input[name="user"]', username)
    page.fill('input[name="password"]', password)
    page.locator('input[type="submit"]').click()

    print("  [auth] Waiting for redirect back to BCAP...")
    page.wait_for_url("**/bcap/**", timeout=60_000)
    page.wait_for_timeout(3000)
    print(f"  [auth] Logged in at {page.url}")

    if forwarder:
        forwarder.stop()


def _is_logged_in(page: Page) -> bool:
    page.goto(f"{BASE_URL}/search", timeout=60_000)
    page.wait_for_timeout(3000)

    return "/search" in page.url and "logon" not in page.url and "auth" not in page.url


@pytest.fixture(scope="session", autouse=True)
def _manage_caches() -> None:
    if os.environ.get("INTEGRATION_CLEAR_CACHE", "0") == "1":
        _clear_caches()


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def _launch_args() -> dict:
    args = ["--no-sandbox", "--disable-setuid-sandbox"]

    return {
        "headless": IN_DOCKER,
        "args": args,
    }


@pytest.fixture(scope="session")
def _context_args() -> dict:
    return {
        "viewport": {"height": 900, "width": 1600},
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(
    _launch_args: dict,
    browser_type_launch_args: dict,
) -> dict:
    return {**browser_type_launch_args, **_launch_args}


@pytest.fixture(scope="session")
def browser_context_args(
    _context_args: dict,
    browser_context_args: dict,
) -> dict:
    return {**browser_context_args, **_context_args}


@pytest.fixture(scope="session")
def browser(playwright: Playwright, _launch_args: dict) -> Browser:
    if CDP_ENDPOINT:
        endpoint = CDP_ENDPOINT

        if not endpoint.startswith("ws://"):
            try:
                with urllib.request.urlopen(f"{endpoint}/json/version") as resp:  # noqa: S310
                    data = json.loads(resp.read())
                    endpoint = data["webSocketDebuggerUrl"]
            except Exception:
                logger.debug("CDP version lookup failed, using endpoint as-is")

            if not endpoint.startswith("ws://"):
                endpoint = CDP_ENDPOINT

        browser = playwright.chromium.connect_over_cdp(endpoint)
        yield browser
        browser.close()
        return

    browser = playwright.chromium.launch(**_launch_args)
    yield browser
    browser.close()


@pytest.fixture(scope="session")
def context(browser: Browser, browser_context_args: dict) -> BrowserContext:
    if CDP_ENDPOINT and browser.contexts:
        yield browser.contexts[0]
        return

    context = browser.new_context(**browser_context_args)
    yield context
    context.close()


@pytest.fixture(scope="session")
def page(context: BrowserContext) -> Page:
    if CDP_ENDPOINT:
        pages = context.pages

        if pages:
            yield pages[0]
            return

    page = context.new_page()
    yield page
    page.close()


@pytest.fixture(scope="session", autouse=True)
def _login(page: Page) -> None:
    if _is_logged_in(page):
        print("\n  [auth] Already logged in")
        return

    _do_idir_login(page)
