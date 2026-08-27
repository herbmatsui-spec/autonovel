"""tests/unit/test_bible_service_erotic.py
BibleService および PromptManager における官能パラメータの統合テスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.models.planning_config import PlanningConfig
from prompts.manager import PromptManager


@pytest.mark.asyncio
async def test_prompt_manager_bible_creation_with_erotic():
    pm = PromptManager()
    prompt = await pm.build_bible_creation_prompt(
        bible_core_schema={"title": "test"},
        genre="ダークファンタジー",
        keywords="契約, 執着",
        concept="悪魔と令嬢の愛憎劇",
        target_eps=5,
        enable_erotic=True,
        erotic_intensity=3,
    )

    assert "官能・成人向け企画指針" in prompt
    assert "過激度: 3" in prompt


@pytest.mark.asyncio
async def test_prompt_manager_plot_batch_with_erotic():
    pm = PromptManager()
    bible_json = '{"title": "愛の試練", "genre": "ロマンス", "concept": "許されぬ恋", "mc_profile": {"name": "エリス"}}'
    prompt = await pm.build_ultra_fast_plot_batch_prompt(
        bible_json_str=bible_json,
        ep_range=[1, 2],
        enable_erotic=True,
        erotic_intensity=2,
    )

    assert "官能・情愛プロット配置指針" in prompt
    assert "強度: 2" in prompt
