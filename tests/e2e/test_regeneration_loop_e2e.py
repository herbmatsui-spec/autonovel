"""End-to-End Test: BookScore < 70 Targeted Regeneration Loop (Step 70).

Verifies that:
1. When BookScore is below 70, AuditAggregatorNode generates a targeted regeneration directive
   for the lowest scoring dimension and routes back to WRITING with should_retry=True.
2. The revised draft addressing the directive achieves a passing score (>= 70) and routes to ILLUSTRATION.
3. If max_retries is reached, it terminates the loop and proceeds downstream without infinite recursion.
"""

import pytest

from src.agents.orchestrator import AgentContext, AgentName
from src.agents.specialists.adapter import AuditAggregatorNode, load_audit_weights
from src.services.audit_aggregator import AuditAggregator
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


class LowQualityMockLLM:
    """Returns low scores for draft with contradictions and weak hooks."""

    async def ainvoke(self, prompt: str, **kwargs):
        class Resp:
            def __init__(self, content):
                self.content = content

        text = str(prompt)
        if "Consistency" in text or "矛盾" in text:
            # Low consistency score
            content = '{"score": 45.0, "critique": "死んだはずの仲間が説明なしに現れており重大な論理矛盾があります。", "suggestions": ["死亡キャラの登場理由を修正するか別キャラに置換"]}'
        elif "Reader Hook" in text or "引き" in text:
            content = '{"score": 52.0, "critique": "冒頭に引きがなく、結末も平坦でクリフハンガーがありません。", "suggestions": ["末尾に謎を提示"]}'
        else:
            content = '{"score": 60.0, "critique": "平均以下の品質です。", "suggestions": ["表現の推敲"]}'

        return Resp(content)


class HighQualityMockLLM:
    """Returns high scores for improved revised draft."""

    async def ainvoke(self, prompt: str, **kwargs):
        class Resp:
            def __init__(self, content):
                self.content = content

        text = str(prompt)
        if "Consistency" in text or "矛盾" in text:
            content = '{"score": 92.0, "critique": "設定矛盾が完全に解消され、論理的一貫性が保たれています。", "suggestions": []}'
        elif "Reader Hook" in text or "引き" in text:
            content = '{"score": 88.0, "critique": "鮮烈なクリフハンガーが追加され読者牽引力が大幅に向上しました。", "suggestions": []}'
        else:
            content = '{"score": 86.0, "critique": "高品質な仕上がりです。", "suggestions": []}'

        return Resp(content)


@pytest.mark.asyncio
async def test_targeted_regeneration_loop_e2e():
    weights = load_audit_weights()

    # -----------------------------------------------------------------
    # Step 1: 初回評価 (低品質ドラフト -> スコア < 70)
    # -----------------------------------------------------------------
    low_llm = LowQualityMockLLM()
    specialists_round1 = [
        ConsistencyAuditor(llm=low_llm),
        CreativityAuditor(llm=low_llm),
        ReaderHookAuditor(llm=low_llm),
        EmotionCurveAuditor(llm=low_llm),
        StyleAuditor(llm=low_llm),
        FactualAuditor(llm=low_llm),
        StructureAuditor(llm=low_llm),
        MultimodalAuditor(llm=low_llm),
    ]
    aggregator1 = AuditAggregator(specialists=specialists_round1, weights=weights)
    node1 = AuditAggregatorNode(aggregator=aggregator1)

    ctx = AgentContext(
        book_id=10,
        branch_id=1,
        ep_num=1,
        artifacts={
            "drafted_text": "昨日の戦いで死んだはずの仲間が朝ごはんを食べていた。今日はいい天気だ。",
            "world_bible": {"characters": {"仲間": {"alive": False, "status": "deceased"}}},
            "illustration_prompt": "朝食を食べる仲間たち",
        },
    )

    res1 = await node1.execute(ctx)

    # 70点未満なので再生成ループが発動すること
    assert res1.artifacts["audit_score"] < 70.0
    assert res1.should_retry is True
    assert res1.next_agent == AgentName.WRITING
    assert res1.artifacts["audit_retry_count"] == 1
    assert res1.artifacts["lowest_dimension"] == "consistency"
    assert "再生成指示 - 重点改善項目: consistency" in res1.artifacts["regeneration_directive"]
    assert "死亡キャラ" in res1.artifacts["regeneration_directive"]

    # -----------------------------------------------------------------
    # Step 2: 再生成実行 (指示を反映した改訂ドラフト -> スコア >= 70)
    # -----------------------------------------------------------------
    # 再生成エージェントが指示を受け取り改訂ドラフトを作成
    ctx.artifacts.update(res1.artifacts)
    ctx.artifacts["drafted_text"] = (
        "昨日の戦いで仲間を失ったセシルは、冷たい朝の空気の中で一人立ち上がった。"
        "しかし食卓の上には、誰かが残したはずのない謎のメモが置かれていた……！"
    )

    high_llm = HighQualityMockLLM()
    specialists_round2 = [
        ConsistencyAuditor(llm=high_llm),
        CreativityAuditor(llm=high_llm),
        ReaderHookAuditor(llm=high_llm),
        EmotionCurveAuditor(llm=high_llm),
        StyleAuditor(llm=high_llm),
        FactualAuditor(llm=high_llm),
        StructureAuditor(llm=high_llm),
        MultimodalAuditor(llm=high_llm),
    ]
    aggregator2 = AuditAggregator(specialists=specialists_round2, weights=weights)
    node2 = AuditAggregatorNode(aggregator=aggregator2)

    res2 = await node2.execute(ctx)

    # スコアが改善し、合格して次工程（ILLUSTRATION）へ進むこと
    assert res2.artifacts["audit_score"] >= 80.0
    assert res2.should_retry is False
    assert res2.next_agent == AgentName.ILLUSTRATION
    assert res2.artifacts["specialist_scores"]["consistency"] == 92.0


@pytest.mark.asyncio
async def test_regeneration_loop_max_retries_termination():
    """Verify that loop does not exceed max_retries and safely exits to ILLUSTRATION."""
    weights = load_audit_weights()
    low_llm = LowQualityMockLLM()
    specialists = [
        ConsistencyAuditor(llm=low_llm),
        CreativityAuditor(llm=low_llm),
        ReaderHookAuditor(llm=low_llm),
        EmotionCurveAuditor(llm=low_llm),
        StyleAuditor(llm=low_llm),
        FactualAuditor(llm=low_llm),
        StructureAuditor(llm=low_llm),
        MultimodalAuditor(llm=low_llm),
    ]
    aggregator = AuditAggregator(specialists=specialists, weights=weights)
    node = AuditAggregatorNode(aggregator=aggregator)

    # Already at max_retries (2)
    ctx = AgentContext(
        book_id=10,
        branch_id=1,
        ep_num=1,
        artifacts={
            "drafted_text": "依然として矛盾だらけの文章。",
            "audit_retry_count": 2,
        },
    )

    res = await node.execute(ctx)

    # スコアは70未満だがリトライ上限到達のため、これ以上の再試行は停止してILLUSTRATIONへ進む
    assert res.artifacts["audit_score"] < 70.0
    assert res.should_retry is False
    assert res.next_agent == AgentName.ILLUSTRATION
