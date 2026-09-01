"""官能エージェント高度化（語彙刷新・LLM評価・GraphRAG連携・挿絵プロンプト）のテスト."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock

from src.agents.erotic.evaluator import EroticQualityReport, EroticQualityScorer
from src.agents.erotic.continuity import SceneStateSnapshot
from src.agents.erotic_enhancer import EroticEnhancer


def test_erotic_quality_scorer_clean_keywords():
    """クリーンな日本語語彙によるキーワードベース品質評価の動作検証."""
    scorer = EroticQualityScorer()
    sample_text = (
        "彼女の温もりが伝わり、吐息が首筋にかかる。\n\n"
        "愛おしさと切なさが胸を満たし、背徳感に苛まれながらも快楽に耽溺していく。"
    )

    report = scorer.score_quality(sample_text)

    assert isinstance(report, EroticQualityReport)
    assert report.overall_score > 0.0
    assert report.sensuality_score > 0.0
    assert report.emotional_score > 0.0
    assert report.psychological_score > 0.0
    assert report.details["sensuality_matches"] >= 1
    assert report.details["emotional_matches"] >= 1
    assert report.details["psychological_matches"] >= 1


def test_erotic_quality_scorer_empty():
    """空テキスト時のゼロスコア動作検証."""
    scorer = EroticQualityScorer()
    report = scorer.score_quality("")
    assert report.overall_score == 0.0


def test_erotic_quality_scorer_llm_as_a_judge():
    """LLM-as-a-Judge による精密評価と Pydantic パースの検証."""
    scorer = EroticQualityScorer()
    mock_llm = MagicMock()
    mock_llm.generate.return_value = (
        '{"overall_score": 88.5, "sensuality_score": 92.0, "emotional_score": 85.0, '
        '"psychological_score": 90.0, "technical_score": 87.0, '
        '"details": {"feedback": "心理的葛藤と吐息の描写が秀逸"}}'
    )

    report = scorer.evaluate_quality_with_llm("テスト本文", llm_adapter=mock_llm)

    assert report.overall_score == 88.5
    assert report.sensuality_score == 92.0
    assert report.details["eval_method"] == "llm_as_a_judge"
    assert "feedback" in report.details


def test_erotic_quality_scorer_llm_fallback():
    """LLM呼び出し失敗時にキーワードスコアラーへ自動フォールバックすることを検証."""
    scorer = EroticQualityScorer()
    mock_llm = MagicMock()
    mock_llm.generate.side_effect = Exception("API connection error")

    sample_text = "熱い体温と吐息、愛おしい感情。"
    report = scorer.evaluate_quality_with_llm(sample_text, llm_adapter=mock_llm)

    assert report.overall_score > 0.0
    assert report.details["eval_method"] == "keyword_heuristic"


def test_erotic_enhancer_graphrag_resolution():
    """GraphRAG の関係性データに応じたパラメータ自動最適化の検証."""
    mock_agent = MagicMock()
    enhancer = EroticEnhancer(agent=mock_agent)

    # 1. 敵対関係 (HATES)
    hates_context = {
        "relationship_type": "HATES",
        "graph_context": "アルスは敵対する宰相と因縁がある",
    }
    hates_params = enhancer._resolve_graphrag_parameters(hates_context)
    assert hates_params["psychology_depth"] >= 85
    assert hates_params["default_consent"] == "implicit"
    assert "intro" in hates_params["pace_ratios"]

    # 2. 主従関係 (MASTER_SERVANT)
    master_context = {
        "relationship_type": "MASTER_SERVANT",
        "graph_context": "主従関係にある",
    }
    master_params = enhancer._resolve_graphrag_parameters(master_context)
    assert master_params["psychology_depth"] >= 80
    assert master_params["metaphor_density"] == 65

    # 3. 恋人関係 (LOVES)
    loves_context = {
        "relationship_type": "LOVES",
        "graph_context": "長年の恋人関係",
    }
    loves_params = enhancer._resolve_graphrag_parameters(loves_context)
    assert loves_params["default_consent"] == "mutual"
    assert "touch" in loves_params["sensory_weights"]


def test_scene_snapshot_to_illustration_prompt():
    """SceneStateSnapshot からの画像生成プロンプト構築検証."""
    snapshot = SceneStateSnapshot(
        character_name="セリア",
        scene_type="erotic",
        time_of_day="night",
        attitude="sensual",
        injury_level="none",
    )

    prompt = snapshot.to_illustration_prompt(additional_tags=["silver hair", "bedroom"])

    assert "1girl, セリア" in prompt
    assert "night" in prompt
    assert "blushing" in prompt
    assert "silver hair" in prompt
    assert "masterpiece, best quality" in prompt
