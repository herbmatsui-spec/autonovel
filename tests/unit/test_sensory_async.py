"""Unit tests for asynchronous sensory expansion module (Part 2)."""
import pytest
import asyncio
import time
from unittest.mock import MagicMock
from src.agents.enrichment.sensory import (
    EmotionSpan,
    detect_abstract_emotions,
    generate_sensory_details,
    replace_with_sensory_expansion,
    expand_sensory_details_pipeline,
    _call_llm_async,
    _fallback_sensory_details,
    EMOTION_TO_SENSORY_MAP,
)
from src.agents.enrichment_agent import EnrichmentAgent


@pytest.mark.asyncio
async def test_detect_abstract_emotions_inflections():
    """連用形（-く）、名詞化（-さ）、過去形（-かった）など多様な活用形を検出できること"""
    text = "恐ろしく冷たい風が吹き、彼は悲しく笑った。怒りで拳を握る。"
    spans = detect_abstract_emotions(text)
    emotions = [s.emotion for s in spans]
    assert "fear" in emotions
    assert "sadness" in emotions
    assert "anger" in emotions


@pytest.mark.asyncio
async def test_generate_sensory_details_async_execution():
    """generate_sensory_details が非同期コルーチンとして実行され五感描写を返すこと"""
    span = EmotionSpan(0, 4, "sadness", 0.8, "悲しかった")
    details = await generate_sensory_details(
        emotion_span=span,
        scene_context="雨の夜、街灯の下",
        pov="third_person",
    )
    assert len(details) >= 1
    # タグプレフィックス付きで返されること
    assert any(d.startswith("[") for d in details)


@pytest.mark.asyncio
async def test_call_llm_async_dispatch_types():
    """同期・非同期・LangChain・Callable等、各種LLMインターフェースを統一非同期ディスパッチできること"""
    # 1. generate (同期モック)
    mock_sync = MagicMock()
    mock_sync.generate.return_value = "同期生成された五感描写"
    res1 = await _call_llm_async(mock_sync, "prompt")
    assert res1 == "同期生成された五感描写"

    # 2. generate (非同期モック)
    class AsyncGenLLM:
        async def generate(self, prompt):
            return "非同期generate五感描写"
    res2 = await _call_llm_async(AsyncGenLLM(), "prompt")
    assert res2 == "非同期generate五感描写"

    # 3. ainvoke (LangChain 形式)
    class LangChainLLM:
        async def ainvoke(self, prompt):
            m = MagicMock()
            m.content = "LangChain五感描写"
            return m
    res3 = await _call_llm_async(LangChainLLM(), "prompt")
    assert res3 == "LangChain五感描写"

    # 4. callable (同期関数)
    res4 = await _call_llm_async(lambda p: "Callable五感描写", "prompt")
    assert res4 == "Callable五感描写"


@pytest.mark.asyncio
async def test_sensory_timeout_protection():
    """LLM呼び出しがタイムアウトした場合に安全にフォールバックしハングしないこと"""
    span = EmotionSpan(0, 4, "fear", 0.9, "恐ろしい")

    class SlowLLM:
        async def ainvoke(self, prompt: str):
            await asyncio.sleep(1.0)
            return "遅い応答"

    start = time.time()
    details = await generate_sensory_details(
        emotion_span=span,
        scene_context="暗闇",
        pov="third_person",
        llm=SlowLLM(),
        timeout_seconds=0.05,
    )
    duration = time.time() - start

    assert duration < 0.3
    assert len(details) >= 1
    # フォールバック描写が返されていること
    assert any("背中" in d or "心音" in d or "瞳孔" in d for d in details)


@pytest.mark.asyncio
async def test_parallel_expansion_with_gather():
    """複数感情スパンが asyncio.gather により並列実行されること"""
    text = "彼は悲しかった。そして怒りが湧き、恐ろしくなった。"

    class MockParallelLLM:
        async def ainvoke(self, prompt: str):
            await asyncio.sleep(0.08)
            return "並列五感描写。"

    start = time.time()
    enriched, meta = await expand_sensory_details_pipeline(
        text=text,
        scene_context="戦火の街",
        pov="third_person",
        llm=MockParallelLLM(),
        timeout_seconds=2.0,
    )
    duration = time.time() - start

    # 直列(0.24s)ではなく並列(0.18s未満)で完了
    assert duration < 0.20
    assert len(meta) == 3
    assert "並列五感描写" in enriched


@pytest.mark.asyncio
async def test_fallback_sensory_details_on_failure():
    """LLM例外発生時でもクラッシュせずフォールバック描写を返すこと"""
    span = EmotionSpan(0, 2, "joy", 0.9, "歓喜")

    class FailingLLM:
        def generate(self, prompt: str):
            raise ConnectionResetError("Remote disconnected")

    details = await generate_sensory_details(
        emotion_span=span,
        scene_context="祝宴の広場",
        pov="third_person",
        llm=FailingLLM(),
        timeout_seconds=1.0,
    )
    assert len(details) >= 1
    assert any("陽射し" in d or "笑顔" in d or "花" in d for d in details)


@pytest.mark.asyncio
async def test_enrichment_agent_sensory_integration():
    """EnrichmentAgent が非同期五感パイプラインを問題なく実行できること"""
    agent = EnrichmentAgent(llm=None)
    text = "少女は恐怖に震えていた。"
    context = {"pov": "third_person", "scene_context": "廃墟"}

    enriched, meta = await agent._expand_sensory_details(text, context)
    assert len(enriched) > len(text)
    assert len(meta) >= 1
    assert meta[0]["emotion"] == "fear"
