import json
import os
import pytest
from core.session import SessionManager, DEFAULT_SESSION


class TestSessionManager:
    def test_load_nonexistent(self, tmp_path):
        mgr = SessionManager(primary_dir=str(tmp_path), fallback_dir=str(tmp_path / "fallback"))
        session = mgr.load()
        assert session == DEFAULT_SESSION

    def test_save_and_load(self, tmp_path):
        mgr = SessionManager(primary_dir=str(tmp_path), fallback_dir=str(tmp_path / "fallback"))
        data = {**DEFAULT_SESSION, "last_search": "번역", "threshold": 70}
        mgr.save(data)
        loaded = mgr.load()
        assert loaded["last_search"] == "번역"
        assert loaded["threshold"] == 70

    def test_fallback_dir_when_primary_not_writable(self, tmp_path):
        primary = str(tmp_path / "readonly" / "nested")
        fallback = str(tmp_path / "fallback")
        os.makedirs(fallback, exist_ok=True)
        mgr = SessionManager(primary_dir=primary, fallback_dir=fallback)
        data = {**DEFAULT_SESSION, "ui_language": "en"}
        mgr.save(data)
        loaded = mgr.load()
        assert loaded["ui_language"] == "en"

    def test_corrupt_session_returns_default(self, tmp_path):
        session_file = tmp_path / "session.json"
        session_file.write_text("not valid json{{{")
        mgr = SessionManager(primary_dir=str(tmp_path), fallback_dir=str(tmp_path / "fb"))
        session = mgr.load()
        assert session == DEFAULT_SESSION

    def test_saves_column_mappings(self, tmp_path):
        mgr = SessionManager(primary_dir=str(tmp_path), fallback_dir=str(tmp_path / "fb"))
        data = {
            **DEFAULT_SESSION,
            "column_mappings": {
                "C:/Work/TM.xlsx": {"source": "A", "targets": ["B", "C"]},
            },
        }
        mgr.save(data)
        loaded = mgr.load()
        assert "C:/Work/TM.xlsx" in loaded["column_mappings"]
