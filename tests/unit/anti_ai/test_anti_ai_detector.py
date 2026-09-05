"""Unit tests for AntiAIDetector specialist auditor."""

from __future__ import annotations

import pytest

from src.agents.specialists.anti_ai_detector import AntiAIDetector


AI_TEXT = """しかし、朝が来た。しかし、昼が来た。しかし、夜が来た。
私は悲しかったと思った。深い洞察を得たと思った。
それは素晴らしい一日だった。重要なことであった。"""

CLEAN_TEXT = "雨が降り始めた。傘もなく、駆け出した。"


class TestAntiAIDetector:
    def test_returns_score_in_range(self) -> None:
        """スコアは0-100の範囲"""
        import asyncio
        auditor = AntiAIDetector()
        result = asyncio.run(auditor.audit({"draft_text": AI_TEXT}))
        assert 0 <= result.score <= 100

    def test_empty_text_returns_zero(self) -> None:
        """空テキストはスコア0"""
        import asyncio
        auditor = AntiAIDetector()
        result = asyncio.run(auditor.audit({"draft_text": ""}))
        assert result.score == 0.0

    def test_missing_draft_text_returns_zero(self) -> None:
        """draft_text がなければスコア0"""
        import asyncio
        auditor = AntiAIDetector()
        result = asyncio.run(auditor.audit({}))
        assert result.score == 0.0

    def test_includes_category_scores_in_feedback(self) -> None:
        """フィードバックにカテゴリ別スコアを含む"""
        import asyncio
        auditor = AntiAIDetector()
        result = asyncio.run(auditor.audit({"draft_text": AI_TEXT}))
        assert "category_scores" in result.feedback
        assert "total_violations" in result.feedback
        assert "total_score" in result.feedback

    def test_sync_fallback_works(self) -> None:
        """同期フォールバックが動作"""
        auditor = AntiAIDetector()
        result = auditor._sync_audit({"draft_text": AI_TEXT})
        assert 0 <= result.score <= 100
        assert result.degraded is True

    def test_specialist_name(self) -> None:
        """specialist_name が正しく設定"""
        auditor = AntiAIDetector()
        assert auditor.specialist_name == "anti_ai"

    def test_clean_text_high_score(self) -> None:
        """クリーンなテキストは高いスコア"""
        import asyncio
        auditor = AntiAIDetector()
        result = asyncio.run(auditor.audit({"draft_text": CLEAN_TEXT}))
        assert result.score >= 95.0

    def test_suggestions_for_low_scores(self) -> None:
        """低スコア時に提案が含まれる"""
        import asyncio
        auditor = AntiAIDetector()
        result = asyncio.run(auditor.audit({"draft_text": AI_TEXT}))
        if result.score < 70:
            assert len(result.suggestions) > 0

    def test_ai_text_triggers_violations(self) -> None:
        """AIテキストは違反を検出"""
        import asyncio
        auditor = AntiAIDetector()
        result = asyncio.run(auditor.audit({"draft_text": AI_TEXT}))
        assert result.feedback["total_violations"] > 0

    def test_to_dict_includes_all_fields(self) -> None:
        """to_dict() が全フィールドを含む"""
        import asyncio
        auditor = AntiAIDetector()
        result = asyncio.run(auditor.audit({"draft_text": AI_TEXT}))
        d = result.to_dict()
        assert "specialist_name" in d
        assert "score" in d
        assert "feedback" in d
        assert "suggestions" in d
