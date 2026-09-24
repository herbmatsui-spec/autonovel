"""Unit tests for fused_emotional_context.j2 template."""
from src.pipeline.prompt_builder import get_jinja_env


def test_render_with_conflicts():
    template = get_jinja_env().get_template("fused_emotional_context.j2")

    high_confidence = [
        {"source": "A", "target": "B", "emotion_ja": "恐怖", "value": 0.8, "cause": "第14話裏切り", "primary_source": "annotation"},
    ]
    medium_confidence = [
        {"source": "A", "target": "C", "emotion_ja": "緊張", "value": 0.4, "cause": "", "primary_source": "rule_engine"},
    ]
    low_confidence = [
        {"source": "C", "target": "A", "emotion_ja": "好意", "value": 0.2, "cause": "", "primary_source": "pipeline"},
    ]
    conflicts = [
        {"pair": ("A", "D"), "emotion_ja": "信頼", "sources": [("annotation", 0.7, 1.0), ("pipeline", -0.5, 0.5)]},
    ]

    rendered = template.render(
        high_confidence=high_confidence,
        medium_confidence=medium_confidence,
        low_confidence=low_confidence,
        conflicts=conflicts,
    )

    assert "[直前話からの引き継ぎ感情（融合済み）]" in rendered
    assert "高信頼度（作者指定・プロット整合）" in rendered
    assert "A→B: 恐怖(0.8) - 第14話裏切り [annotation]" in rendered
    assert "中信頼度（プロットルール推定）" in rendered
    assert "A→C: 緊張(0.4) [rule_engine]" in rendered
    assert "低信頼度（自動抽出・参考）" in rendered
    assert "C→A: 好意(0.2) [pipeline]" in rendered
    assert "⚠ 矛盾検出（要確認）" in rendered
    assert "A→D: annotation=信頼(0.7) vs pipeline=信頼(-0.5)" in rendered
