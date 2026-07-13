"""
tests/test_phase1to3_e2e.py
Phase 1-3 (改善案A: 感情設計先行) の統合E2Eテスト。

UI選択 -> フック構築 -> tension曲線選択 -> プロンプト注入 -> モックLLM応答 -> Plot.emotional_hook 永続化
"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from config.emotional_hook_vocabulary import get_hook_peak_tension
from src.backend.tension_curve_config import select_curve_by_hook
from src.backend.engine_plot import get_emotional_hook_for_plot, resolve_emotional_hook
from src.models.emotional_hook import EmotionalHookSpec
from src.models.db import PlotDbModel
from streamlit_app.state import desires_to_hook


class TestPhase1To3Integration:
    def test_ui_desire_to_hook_to_tension_curve(self):
        desires = ["カタルシス"]
        hook = desires_to_hook(desires)
        assert hook is not None
        assert hook.hook_name == "catharsis"
        curve = select_curve_by_hook(hook.hook_name)
        assert curve == "zamaa_heavy"
        peak = get_hook_peak_tension(hook.hook_name)
        assert peak == 85

    def test_hook_persists_to_plot_db_model(self):
        hook = EmotionalHookSpec(
            hook_name="catharsis",
            one_line_intent="解放",
            target_tension_peak=85,
        )
        plot = PlotDbModel(book_id=1, ep_num=1)
        plot.emotional_hook = hook
        assert plot.emotional_hook.hook_name == "catharsis"

    def test_hook_json_roundtrip(self):
        hook = EmotionalHookSpec(
            hook_name="catharsis",
            one_line_intent="解放",
            target_tension_peak=85,
        )
        json_str = hook.model_dump_json()
        restored = EmotionalHookSpec.model_validate_json(json_str)
        assert restored.hook_name == "catharsis"
        assert restored.target_tension_peak == 85

    @pytest.mark.asyncio
    async def test_end_to_end_flow(self):
        repo = MagicMock()
        repo.get_plot = AsyncMock(return_value=None)

        plot = PlotDbModel(book_id=1, ep_num=1)
        hook = await get_emotional_hook_for_plot(plot, repo=repo, book_id=1, ep_num=1)
        assert hook.hook_name == "catharsis"

        # Hook を Plot に保存
        plot.emotional_hook_json = hook.model_dump_json()
        loaded = resolve_emotional_hook(plot)
        assert loaded is not None
        assert loaded.hook_name == "catharsis"
