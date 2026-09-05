"""Unit & integration test for 8 specialist auditors parallel execution with LLM judge (Step 68)."""

import pytest
import asyncio

from src.agents.specialists import (
    ConsistencyAuditor,
    CreativityAuditor,
    ReaderHookAuditor,
    EmotionCurveAuditor,
    StyleAuditor,
    FactualAuditor,
    StructureAuditor,
    MultimodalAuditor,
)
from src.services.audit_aggregator import AuditAggregator, BookScoreResult


class SpecialistDummyLLM:
    """Mock LLM responding with structured JSON tailored to each specialist prompt."""

    async def ainvoke(self, prompt: str, **kwargs):
        class Resp:
            def __init__(self, content):
                self.content = content

        text = str(prompt)
        if "Consistency" in text or "矛盾" in text:
            content = '{"score": 88.0, "critique": "設定矛盾はなく、登場人物の生存状態も整合しています。", "suggestions": []}'
        elif "Creativity" in text or "独創性" in text:
            content = '{"score": 85.0, "critique": "比喩表現が鮮烈で、独創的な世界観が展開されています。", "suggestions": ["後半の語彙をさらに豊かに"]}'
        elif "Reader Hook" in text or "引きの強さ" in text or "クリフハンガー" in text:
            content = '{"score": 90.0, "critique": "冒頭の謎かけと末尾のクリフハンガーが読者を強く惹きつけます。", "suggestions": []}'
        elif "Emotion Curve" in text or "感情曲線" in text or "カタルシス" in text:
            content = '{"score": 82.0, "critique": "緊張の高まりと結末のカタルシスがバランスよく描かれています。", "suggestions": []}'
        elif "Style" in text or "文体" in text or "トーン" in text:
            content = '{"score": 89.0, "critique": "語尾と口調が一貫しており、格調高い文体が維持されています。", "suggestions": []}'
        elif "Factual" in text or "時代考証" in text or "事実関係" in text:
            content = '{"score": 92.0, "critique": "時代考証および作中ルールの科学的・魔術的整合性が確認されました。", "suggestions": []}'
        elif "Structure" in text or "起承転結" in text or "構成" in text:
            content = '{"score": 86.0, "critique": "プロットの起承転結が綺麗に消化され、テンポも良好です。", "suggestions": []}'
        elif "Multimodal" in text or "挿絵" in text:
            content = '{"score": 94.0, "critique": "本文の決戦シーンと挿絵指示の構図・ライティングが完全に一致しています。", "suggestions": []}'
        else:
            content = '{"score": 80.0, "critique": "良好な品質です。", "suggestions": []}'

        # Simulate small async network latency to verify asyncio.gather concurrency
        await asyncio.sleep(0.01)
        return Resp(content)


@pytest.fixture
def standard_weights():
    return {
        "consistency": 0.20,
        "creativity": 0.15,
        "reader_hook": 0.15,
        "emotion_curve": 0.10,
        "style": 0.10,
        "factual": 0.10,
        "structure": 0.10,
        "multimodal": 0.10,
    }


@pytest.mark.asyncio
async def test_all_8_specialists_parallel_execution_with_llm(standard_weights):
    mock_llm = SpecialistDummyLLM()
    specialists = [
        ConsistencyAuditor(llm=mock_llm),
        CreativityAuditor(llm=mock_llm),
        ReaderHookAuditor(llm=mock_llm),
        EmotionCurveAuditor(llm=mock_llm),
        StyleAuditor(llm=mock_llm),
        FactualAuditor(llm=mock_llm),
        StructureAuditor(llm=mock_llm),
        MultimodalAuditor(llm=mock_llm),
    ]

    aggregator = AuditAggregator(specialists=specialists, weights=standard_weights)

    ctx = {
        "draft_text": "城門の前で勇者は立ち止まった。なぜ彼が選ばれたのか？その謎はまだ明かされていない。空には巨大な暗雲が立ち込め、雷光が閃いた。彼は覚悟を決めて剣を抜いた。",
        "plot_tree": "城門への到達 → 葛藤 → 抜刀と覚悟",
        "illustration_prompts": "暗雲の下、城門の前で雷光を浴びながら剣を抜く勇者。ドラマチックな陰影。",
        "world_bible": {"characters": {"勇者": {"alive": True, "status": "active"}}},
        "style_dna": {"tone": "serious", "person": "third_person"},
    }

    # Parallel audit run
    results = await aggregator.run_all(ctx)
    assert len(results) == 8

    for name, res in results.items():
        assert 0.0 <= res.score <= 100.0, f"Specialist {name} score out of bounds: {res.score}"
        assert not res.degraded, f"Specialist {name} should not be degraded"
        assert res.feedback.get("critique"), f"Specialist {name} missing critique"

    book_score: BookScoreResult = aggregator.aggregate()
    assert 80.0 <= book_score.overall <= 95.0
    assert len(book_score.missing) == 0
    assert book_score.lowest_dimension() is not None


@pytest.mark.asyncio
async def test_partial_llm_failure_graceful_degradation(standard_weights):
    """If some specialists have no LLM, they gracefully fall back without crashing the aggregator."""
    mock_llm = SpecialistDummyLLM()
    specialists = [
        ConsistencyAuditor(llm=mock_llm),
        CreativityAuditor(llm=None),  # Fallback to rule-based
        ReaderHookAuditor(llm=mock_llm),
        EmotionCurveAuditor(llm=None),  # Fallback to rule-based
        StyleAuditor(llm=mock_llm),
        FactualAuditor(llm=None),  # Fallback to rule-based
        StructureAuditor(llm=mock_llm),
        MultimodalAuditor(llm=mock_llm),
    ]

    aggregator = AuditAggregator(specialists=specialists, weights=standard_weights)

    ctx = {
        "draft_text": "冷たい風が吹いた。なぜここにいるのか？少年は立ち上がり、歩き始めた。",
        "plot_tree": "立ち上がり → 出発",
        "illustration_prompts": "風吹く荒野に立つ少年",
        "world_bible": {},
    }

    results = await aggregator.run_all(ctx)
    assert len(results) == 8

    # LLM-present specialists
    assert not results["consistency"].degraded
    assert not results["reader_hook"].degraded
    assert not results["style"].degraded
    assert not results["structure"].degraded
    assert not results["multimodal"].degraded

    # LLM-absent specialists (degraded to rule-based)
    assert results["creativity"].degraded
    assert results["emotion_curve"].degraded
    assert results["factual"].degraded

    # Aggregator successfully computes overall score
    book_score = aggregator.aggregate()
    assert 0.0 <= book_score.overall <= 100.0
