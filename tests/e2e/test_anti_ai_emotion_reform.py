"""
E2E integration test for Anti-AI Emotion Reform and Syllogism Elimination.
PLAN 03 - Step 12: 優等生的文章が排除され、エゴと毒が効いた文章が出力されるE2Eテスト
"""
from __future__ import annotations

import pytest

from src.services.anti_ai.detectors import EmotionSyllogismDetector
from src.services.anti_ai.orchestrator import RuleBasedAntiAIDetector
from src.services.anti_ai.rewrite_directive_generator import generate_syllogism_rewrite_directive


@pytest.mark.asyncio
async def test_anti_ai_emotion_reform_pipeline_e2e():
    """
    E2Eテスト:
    1. 初回生成: AI優等生病（三段論法）を含む文章が出力される。
    2. 監査: EmotionSyllogismDetectorが三段論法を検知し、ペナルティとリライト指示を発行する。
    3. リライト: 指示を反映した第2世代の文章は、身体的生理反応と生々しい打算・毒気に置換される。
    4. 最終検証: 三段論法違反がゼロとなり、Anti-AI総合スコアが合格水準に達すること。
    """
    # 1. AI優等生的文章（初回生成）
    first_draft_ai = (
        "アルトは怒りを感じた。なぜなら勇者たちに理不尽な追放を宣告されたからだ。\n"
        "しかし、今は耐えるべきだと自分に言い聞かせた。\n"
        "一瞬躊躇したが、気を取り直して一人ダンジョンへ向かった。"
    )

    # 2. 身体言語と毒気・打算に置換された人間的文章（リライト後）
    second_draft_human = (
        "「お前はクビだ」という勇者の嘲笑に、アルトは奥歯をギリリと軋ませた。\n"
        "喉の奥に苦い胃液が競り上がる。『絶対に後悔させてやる。泣きついてきても一滴のポーションも恵んでやらない』\n"
        "口元に冷たい笑みを浮かべ、男は背を向けた。"
    )

    detector = EmotionSyllogismDetector()
    orchestrator = RuleBasedAntiAIDetector()

    # 初回原稿の監査
    violations = detector.detect(first_draft_ai)
    assert len(violations) >= 2, "AI draft must trigger syllogism violations"

    directive = generate_syllogism_rewrite_directive(violations)
    assert "感情説明の外科的切除ディレクティブ" in directive

    # リライト指示を反映した第2世代原稿の監査
    final_violations = detector.detect(second_draft_human)
    assert len(final_violations) == 0, "Humanized draft must have 0 syllogism violations"

    # Anti-AIオーケストレーター総合スコアの確認
    audit_res = orchestrator.detect(second_draft_human)
    assert audit_res.category_scores[detector.category] == 100.0
    assert audit_res.total_score >= 85.0

    # 生々しいエゴ・打算が含まれていることの検証
    assert "後悔させてやる" in second_draft_human or "冷たい笑み" in second_draft_human
    assert "奥歯" in second_draft_human
