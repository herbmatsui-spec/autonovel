"""
tests/test_engine_plot_hook_integration.py
src/backend/engine_plot.py の統合テスト。
"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.engine_plot import (
    ENFORCE_ENTERTAINMENT_FIRST,
    _build_default_hook,
    get_emotional_hook_for_plot,
    resolve_emotional_hook,
)
from src.models.db import PlotDbModel
from src.models.emotional_hook import EmotionalHookSpec


class TestResolveEmotionalHook:
    def test_none_plot_returns_none(self):
        assert resolve_emotional_hook(None) is None

    def test_valid_json_returns_spec(self):
        data = {
            "hook_name": "catharsis",
            "one_line_intent": "解放",
            "target_tension_peak": 85,
        }
        plot = PlotDbModel(book_id=1, ep_num=1, emotional_hook_json=json.dumps(data))
        result = resolve_emotional_hook(plot)
        assert isinstance(result, EmotionalHookSpec)
        assert result.hook_name == "catharsis"

    def test_empty_json_returns_none(self):
        plot = PlotDbModel(book_id=1, ep_num=1, emotional_hook_json="")
        assert resolve_emotional_hook(plot) is None

    def test_invalid_json_returns_none(self):
        plot = PlotDbModel(book_id=1, ep_num=1, emotional_hook_json="not json")
        assert resolve_emotional_hook(plot) is None


class TestGetEmotionalHookForPlot:
    @pytest.mark.asyncio
    async def test_hook_from_plot_json(self):
        data = {
            "hook_name": "catharsis",
            "one_line_intent": "解放",
            "target_tension_peak": 85,
        }
        plot = PlotDbModel(book_id=1, ep_num=1, emotional_hook_json=json.dumps(data))
        hook = await get_emotional_hook_for_plot(plot, repo=None, book_id=1, ep_num=1)
        assert hook.hook_name == "catharsis"

    @pytest.mark.asyncio
    async def test_fallback_to_default_when_no_hook(self):
        plot = PlotDbModel(book_id=1, ep_num=1)
        hook = await get_emotional_hook_for_plot(plot, repo=None, book_id=1, ep_num=1)
        assert hook.hook_name == "catharsis"
        assert hook.target_tension_peak == 85

    @pytest.mark.asyncio
    async def test_repo_load_used_when_plot_has_no_hook(self):
        loaded = PlotDbModel(
            book_id=1, ep_num=1,
            emotional_hook_json=json.dumps({"hook_name": "chilling", "one_line_intent": "寒気", "target_tension_peak": 90})
        )
        repo = MagicMock()
        repo.get_plot = AsyncMock(return_value=loaded)

        plot = PlotDbModel(book_id=1, ep_num=1)
        hook = await get_emotional_hook_for_plot(plot, repo=repo, book_id=1, ep_num=1)
        assert hook.hook_name == "chilling"
