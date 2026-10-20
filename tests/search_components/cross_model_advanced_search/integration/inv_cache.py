from __future__ import annotations

import json

from pathlib import Path

from typing import Any

CACHE_DIR = Path(__file__).resolve().parent / ".cache"
INV_CACHE_FILE = CACHE_DIR / "inventory.json"


class InventoryCache:
    def __init__(self) -> None:
        self._data = self._load()

    def _load(self) -> list[dict[str, Any]] | None:
        if INV_CACHE_FILE.exists():
            with open(INV_CACHE_FILE, "r") as f:
                return json.load(f)

        return None

    def _save(self) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        with open(INV_CACHE_FILE, "w") as f:
            json.dump(self._data, f, indent=2, sort_keys=True)

    def get(self) -> list[dict[str, Any]] | None:
        return self._data

    def put(self, inventory: list[dict[str, Any]]) -> None:
        self._data = inventory
        self._save()
