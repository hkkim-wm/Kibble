import json
import os
from typing import Any, Dict

SESSION_FILENAME = "session.json"

DEFAULT_SESSION: Dict[str, Any] = {
    "last_files": [],
    "column_mappings": {},
    "last_search": "",
    "match_mode": "both",
    "threshold": 50,
    "search_direction": "source",
    "view_mode": "source_target",
    "case_sensitive": False,
    "whole_word": False,
    "font_size": 12,
    "limit": 200,
    "window_size": [1200, 800],
    "window_position": [100, 100],
    "ui_language": "ko",
    "splitter_sizes": [],
}


class SessionManager:
    def __init__(self, primary_dir: str, fallback_dir: str):
        self._primary = os.path.join(primary_dir, SESSION_FILENAME)
        self._fallback = os.path.join(fallback_dir, SESSION_FILENAME)
        self._active_path: str | None = None

    def _resolve_path(self, for_write: bool = False) -> str | None:
        if self._active_path and os.path.exists(self._active_path):
            return self._active_path
        if not for_write:
            if os.path.isfile(self._primary):
                self._active_path = self._primary
                return self._primary
            if os.path.isfile(self._fallback):
                self._active_path = self._fallback
                return self._fallback
            return None
        try:
            os.makedirs(os.path.dirname(self._primary), exist_ok=True)
            with open(self._primary, "a") as f:
                pass
            self._active_path = self._primary
            return self._primary
        except OSError:
            pass
        try:
            os.makedirs(os.path.dirname(self._fallback), exist_ok=True)
            self._active_path = self._fallback
            return self._fallback
        except OSError:
            return None

    def load(self) -> Dict[str, Any]:
        path = self._resolve_path(for_write=False)
        if path is None:
            return dict(DEFAULT_SESSION)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(DEFAULT_SESSION)
            merged.update(data)
            return merged
        except (json.JSONDecodeError, OSError):
            return dict(DEFAULT_SESSION)

    def save(self, data: Dict[str, Any]) -> bool:
        path = self._resolve_path(for_write=True)
        if path is None:
            return False
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except OSError:
            return False
