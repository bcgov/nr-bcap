from __future__ import annotations

import json

from pathlib import Path


CACHE_DIR = Path(__file__).resolve().parent / ".cache"
ADV_CACHE_FILE = CACHE_DIR / "advanced_search_counts.json"


class AdvancedSearchCache:
    def __init__(self) -> None:
        self._data = self._load()

    def _load(self) -> dict:
        if ADV_CACHE_FILE.exists():
            with open(ADV_CACHE_FILE, "r") as f:
                return json.load(f)

        return {}

    def _save(self) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        with open(ADV_CACHE_FILE, "w") as f:
            json.dump(self._data, f, indent=2, sort_keys=True)

    def get(self, graph: str, card: str) -> dict | None:
        key = f"{graph}|{card}"
        return self._data.get(key)

    def put(self, graph: str, card: str, field_counts: dict) -> None:
        key = f"{graph}|{card}"
        self._data[key] = field_counts
        self._save()
