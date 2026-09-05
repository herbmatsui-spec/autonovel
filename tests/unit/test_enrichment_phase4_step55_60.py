"""Unit tests for Phase 4 Enrichment Refinements (Steps 55 to 60)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest
from jinja2 import Template

from src.agents.enrichment.sensory import (
    EmotionSpan,
    generate_sensory_details,
    replace_with_sensory_expansion,
    expand_sensory_details_pipeline,
)
from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.orchestrator import AgentContext, AgentName


def test_step55_sensory_expansion_jinja2_rendering():
    """Step 55: sensory_expansion.jinja2 テンプレートが正常にレンダリングできること."""
    tpl_path = Path("src/prompts/enrichment/sensory_expansion.jinja2")
    assert tpl_path.exists()
    content = tpl_path.read_text(encoding="utf-8")
    
    template = Template(content)
    rendered = template.render(
        emotion="sadness",
        original_phrase="悲しかった",
        scene_context="雨の降る薄暗い裏通り",
        pov="三人称",
        preferred_senses=["tactile", "auditory"],
    )
    assert "sadness" in rendered
    assert "悲しかった" in rendered
    assert "雨の降る薄暗い裏通り" in rendered
    assert "tactile" in rendered


def test_step56_llm_sensory_generation_call():
    """Step 56: generate_sensory_details が LLM を呼び出して高度な展開文を生成すること."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = "冷たい雨が頬を打ち、彼の視界は白く霞んでいた。"

    span = EmotionSpan(
        start=0,
        end=5,
        emotion="sadness",
        intensity=0.8,
        abstract_phrase="悲しかった",
    )

    details = generate_sensory_details(
        emotion_span=span,
        scene_context="雨の戦場",
        pov="三人称",
        llm=mock_llm,
    )
    mock_llm.generate.assert_called_once()
    assert len(details) == 1
    assert "冷たい雨が頬を打ち" in details[0]


def test_step57_no_debug_tags_in_expanded_text():
    """Step 57: 置換後の本文に [visual] や [tactile] などのデバッグタグが残らないこと."""
    text = "彼は悲しかった。立ち尽くしていた。"
    spans = [EmotionSpan(start=2, end=7, emotion="sadness", intensity=0.7, abstract_phrase="悲しかった")]
    raw_details = [["[visual] 涙が零れ落ちた", "[tactile] 頬が冷たく強ばった"]]

    enriched, meta = replace_with_sensory_expansion(text, spans, raw_details)
    # 本文にブラケット付き感覚タグが残っていないこと
    assert "[visual]" not in enriched
    assert "[tactile]" not in enriched
    assert "涙が零れ落ちた" in enriched
    assert "頬が冷たく強ばった" in enriched


def test_step58_token_budget_enforcement():
    """Step 58: トークン予算（1500トークン ≒ 3000文字）超過時の安全なトリミング抑制."""
    agent = EnrichmentAgent()
    original = "元の小説本文。"
    # 巨大な増分（10000文字）
    oversized = original + ("五感描写とトリビアの追加文章。" * 500)

    trimmed = agent._enforce_token_budget(original, oversized)
    # 上限（約3000文字増分）以内に収まり、かつ文末で切り詰められていること
    assert len(trimmed) <= len(original) + 3000 + 10
    assert trimmed.endswith("。")


def test_step59_config_enrichment_enabled():
    """Step 59: config/enrichment.yaml で enabled が True であること."""
    agent = EnrichmentAgent()
    assert agent._config.get("enabled") is True


@pytest.mark.asyncio
async def test_step60_enrichment_agent_exception_fallback():
    """Step 60: LLMや処理中に例外が発生しても drafted_text が1文字も損なわれず無傷で返ること."""
    agent = EnrichmentAgent()
    # 意図的にエラーを起こすため、_enrich_with_trivia をモックして例外送出
    agent._enrich_with_trivia = AsyncMock(side_effect=RuntimeError("LLM API Rate Limit Exceeded"))

    original_draft = "勇者アルカディアは剣を握りしめ、魔王城の扉を押し開けた。"
    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=1,
        artifacts={"drafted_text": original_draft},
    )

    result = await agent.execute(ctx)
    assert result.next_agent == AgentName.AUDIT
    # 原稿テキストが無傷で保持されていること
    assert result.artifacts["drafted_text"] == original_draft
    assert result.artifacts["enriched_text"] == original_draft
    assert "Enrichment failed, using original" in (result.error or "")
