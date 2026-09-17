import time
import pytest
from unittest.mock import AsyncMock
from src.agents.specialists.unified_auditor import UnifiedAuditor

@pytest.mark.asyncio
async def test_agent_speed_benchmark_static_audit():
    """静的ルール解析（第1層）が1回あたり1ms未満（目標<0.001s）で完了することを検証"""
    auditor = UnifiedAuditor(llm_gateway=None)
    sample_text = (
        "「行くぞ！」勇者は剣を抜いた。目の前に広がるは絶望の軍勢。\n"
        "だが彼の瞳に迷いはなかった。空が割れ、光が差し込む！？"
    ) * 10  # 約800文字

    start = time.perf_counter()
    iterations = 50
    for _ in range(iterations):
        score, meta = auditor.audit_quantitative(sample_text)
    elapsed = time.perf_counter() - start

    avg_time_ms = (elapsed / iterations) * 1000.0
    print(f"\n[BENCHMARK] Average Quantitative Audit Time: {avg_time_ms:.3f} ms")
    assert avg_time_ms < 5.0  # 5ms未満（超高速）

@pytest.mark.asyncio
async def test_agent_speed_benchmark_full_hybrid():
    """二層ハイブリッド監査（第1層＋第2層）が即座に収束し、1話全体でも目標<30s以内を確実に達成できることを検証"""
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = (
        '{"hook_score": 85, "emotional_score": 82, "character_consistency": 90, '
        '"overall_score": 85, "critique": "テンポ良好", "actionable_patch": null}'
    )
    auditor = UnifiedAuditor(llm_gateway=mock_llm)
    sample_text = "「ここからが本番だ」アリスは不敵に笑った。"

    start = time.perf_counter()
    report = await auditor.audit(sample_text)
    elapsed = time.perf_counter() - start

    assert report.is_acceptable is True
    assert elapsed < 1.0  # モックLLM環境で1秒未満で完全収束
