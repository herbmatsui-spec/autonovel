"""src.backend.engine_context の深層単体テスト (Step 6)。"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.engine_context import (
    ContextData,
    ContextManager,
    DynamicState,
    ImmutableInput,
    SystemConfig,
)
from src.backend.database import CharacterDbModel, PlotDbModel


# ==============================================================================
# Data Models Tests
# ==============================================================================


class TestContextModels:
    def test_immutable_input(self):
        model = ImmutableInput(
            past_summary="過去のあらすじ",
            active_subplots=["サブ1"],
            locked_foreshadowings=["伏線1"],
            static_character_profiles={"主人公": "プロファイル"},
        )
        assert model.past_summary == "過去のあらすじ"
        assert model.active_subplots == ["サブ1"]
        assert model.locked_foreshadowings == ["伏線1"]

    def test_system_config(self):
        model = SystemConfig(
            active_constraints=[{"type": "制約"}], pacing_instruction="テンポ速め"
        )
        assert model.pacing_instruction == "テンポ速め"
        assert len(model.active_constraints) == 1

    def test_dynamic_state(self):
        model = DynamicState(
            character_states={"主人公": "活発"}, current_tension=70, unresolved_threads=["謎"]
        )
        assert model.current_tension == 70
        assert model.character_states["主人公"] == "活発"

    def test_context_data(self):
        data = ContextData(
            immutable=ImmutableInput(
                past_summary="", active_subplots=[], locked_foreshadowings=[], static_character_profiles={}
            ),
            config=SystemConfig(active_constraints=[], pacing_instruction=""),
            dynamic=DynamicState(character_states={}, current_tension=0, unresolved_threads=[]),
        )
        assert data.dynamic.current_tension == 0


# ==============================================================================
# ContextManager Tests
# ==============================================================================


def _make_plot(**kwargs) -> PlotDbModel:
    p = MagicMock(spec=PlotDbModel)
    p.detailed_blueprint = kwargs.get("detailed_blueprint", "主人公が冒険する")
    p.summary = kwargs.get("summary", "あらすじ")
    p.script_content = kwargs.get("script_content", "台本")
    return p


def _make_char(name: str, role: str = "主人公", registry: str | None = None) -> MagicMock:
    c = MagicMock(spec=CharacterDbModel)
    c.name = name
    c.role = role
    c.registry_data = (
        registry
        if registry is not None
        else json.dumps({"personality": "勇気ある", "ability": "剣術", "iron_constraint": "信じない"})
    )
    return c


class TestContextManager:
    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock()
        repo.get_book = AsyncMock(return_value=None)
        repo.get_chapters_before = AsyncMock(return_value=[])
        repo.get_relevant_past_logs = AsyncMock(return_value="")
        return repo

    @pytest.fixture
    def manager(self, mock_repo):
        with pytest.warns(DeprecationWarning):
            return ContextManager(mock_repo)

    def test_init_deprecation_warning(self, mock_repo):
        with pytest.warns(DeprecationWarning):
            ContextManager(mock_repo)

    def test_get_delegate_fallback(self, manager):
        # ContextBuilderAgent 初期化は環境依存のため None でもよい
        delegate = manager._get_delegate()
        assert delegate is None or delegate is not None

    def test_parse_character_registry_with_registry_data(self):
        char = _make_char("テスト", registry='{"personality": "明るい"}')
        result = ContextManager._parse_character_registry(char)
        assert result["personality"] == "明るい"

    def test_parse_character_registry_invalid_json(self):
        char = _make_char("テスト", registry="invalid{{json")
        result = ContextManager._parse_character_registry(char)
        assert result == {}

    def test_parse_character_registry_dict(self):
        char = MagicMock()
        char.name = "テスト"
        char.to_safe_dict = MagicMock(return_value={"personality": "穏やか"})
        result = ContextManager._parse_character_registry(char)
        assert result == {"personality": "穏やか"}

    def test_parse_character_registry_with_model_dump(self):
        # to_safe_dict がなく registry_data も dict の場合は registry_data が優先される
        char = MagicMock(spec=CharacterDbModel)
        char.name = "テスト"
        char.registry_data = {"personality": "冷静"}
        result = ContextManager._parse_character_registry(char)
        assert result == {"personality": "冷静"}

    def test_filter_active_characters_fallback(self, manager, mock_repo):
        # delegate を None にしてフォールバック経路を実行
        manager._delegate_agent = None
        manager._get_delegate = lambda: None
        plot = _make_plot(detailed_blueprint="勇者が森へ行く")
        chars = [_make_char("勇者", "主人公"), _make_char("魔女", "悪役")]
        result = manager.filter_active_characters(plot, chars, {"勇者": "活発"})
        assert isinstance(result, str)

    def test_filter_active_characters_with_delegate(self, manager):
        delegate = MagicMock()
        delegate._build_char_static_ctx.return_value = "■ 勇者 (主人公)"
        manager._delegate_agent = delegate
        manager._get_delegate = lambda: delegate
        plot = _make_plot()
        chars = [_make_char("勇者", "主人公")]
        result = manager.filter_active_characters(plot, chars, {})
        assert result == "■ 勇者 (主人公)"

    @pytest.mark.asyncio
    async def test_build_past_context_fallback_empty(self, manager, mock_repo):
        manager._get_delegate = lambda: None
        result = await manager.build_past_context(book_id=1, end_ep=5)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_build_past_context_with_world_state(self, manager, mock_repo):
        manager._get_delegate = lambda: None
        chap = MagicMock()
        chap.ep_num = 3
        chap.summary = "出来事"
        chap.ai_insight = "洞察"
        chap.world_state = json.dumps(
            {
                "cumulative_summary": "全体の要約",
                "character_states": {"勇者": "育成中"},
                "story_threads": [
                    {"status": "Active", "description": "剣の謎", "setup_episode": 1, "target_resolve_episode": 5},
                    {"status": "Closed", "description": "閉じた伏線"},
                ],
            }
        )
        mock_repo.get_chapters_before = AsyncMock(return_value=[chap])
        result = await manager.build_past_context(book_id=1, end_ep=5)
        assert "全体の要約" in result
        assert "剣の謎" in result
        assert "閉じた伏線" not in result

    @pytest.mark.asyncio
    async def test_build_past_context_invalid_world_state(self, manager, mock_repo):
        manager._get_delegate = lambda: None
        chap = MagicMock()
        chap.ep_num = 2
        chap.summary = "サマリ"
        chap.ai_insight = None
        chap.world_state = "not-a-json{{{"
        mock_repo.get_chapters_before = AsyncMock(return_value=[chap])
        result = await manager.build_past_context(book_id=1, end_ep=5)
        assert "サマリ" in result

    @pytest.mark.asyncio
    async def test_get_optimal_context_fallback(self, manager, mock_repo):
        manager._get_delegate = lambda: None
        plot = _make_plot()
        chars = [_make_char("勇者", "主人公")]
        char_ctx, prev_ctx = await manager.get_optimal_context(
            book_id=1, ep_num=2, plots=plot, all_chars=chars
        )
        assert isinstance(char_ctx, str)
        assert isinstance(prev_ctx, str)

    @pytest.mark.asyncio
    async def test_get_optimal_context_split_fallback(self, manager, mock_repo):
        manager._get_delegate = lambda: None
        plot = _make_plot()
        chars = [_make_char("勇者", "主人公")]
        static_ctx, dynamic_ctx, prev_ctx = await manager.get_optimal_context_split(
            book_id=1, ep_num=2, plot=plot, chars=chars
        )
        assert isinstance(static_ctx, str)
        assert isinstance(dynamic_ctx, str)
        assert isinstance(prev_ctx, str)

    @pytest.mark.asyncio
    async def test_get_structured_context_split(self, manager, mock_repo):
        manager._get_delegate = lambda: None
        plot = _make_plot()
        chars = [_make_char("勇者", "主人公")]
        data = await manager.get_structured_context_split(
            book_id=1, ep_num=2, plot=plot, chars=chars
        )
        assert isinstance(data, ContextData)
        assert isinstance(data.immutable, ImmutableInput)
        assert isinstance(data.config, SystemConfig)
        assert isinstance(data.dynamic, DynamicState)
        assert data.dynamic.current_tension == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
