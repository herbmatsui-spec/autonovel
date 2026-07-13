"""
tests/test_engine_plot_enforce.py
src/backend/engine_plot.py の面白さ優先順序強制テスト。
"""
import json

import pytest

from src.models.db import PlotDbModel
from src.backend.engine_plot import (
    ENFORCE_ENTERTAINMENT_FIRST,
    ensure_emotional_hook_set,
    resolve_emotional_hook,
)


class TestEnsureEmotionalHookSet:
    def test_no_error_when_enforcement_disabled(self, monkeypatch):
        monkeypatch.setattr("src.backend.engine_plot.ENFORCE_ENTERTAINMENT_FIRST", False)
        plot = PlotDbModel(book_id=1, ep_num=1)
        ensure_emotional_hook_set(plot)  # should not raise

    def test_no_error_when_hook_set(self, monkeypatch):
        monkeypatch.setattr("src.backend.engine_plot.ENFORCE_ENTERTAINMENT_FIRST", True)
        data = {"hook_name": "catharsis", "one_line_intent": "解放", "target_tension_peak": 85}
        plot = PlotDbModel(book_id=1, ep_num=1, emotional_hook_json=json.dumps(data))
        ensure_emotional_hook_set(plot)  # should not raise

    def test_runtime_error_when_hook_missing(self, monkeypatch):
        monkeypatch.setattr("src.backend.engine_plot.ENFORCE_ENTERTAINMENT_FIRST", True)
        plot = PlotDbModel(book_id=1, ep_num=1)
        with pytest.raises(RuntimeError, match="emotional_hook が未設定です"):
            ensure_emotional_hook_set(plot)
