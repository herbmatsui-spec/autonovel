"""Unit tests for AntiAILoopController."""

from __future__ import annotations

import pytest

from src.services.anti_ai.loop_controller import AntiAILoopController
from src.services.anti_ai.models import AICategory, Severity, ViolationSpan


AI_TEXT = """しかし、朝が来た。しかし、昼が来た。しかし、夜が来た。
私は悲しかったと思った。深い洞察を得たと思った。
それは素晴らしい一日だった。重要なことであった。"""

CLEAN_TEXT = "雨が降り始めた。傘もなく、駆け出した。"

EMPTY_TEXT = ""


class TestAntiAILoopController:
    def test_converges_within_max_loops(self) -> None:
        """スコアが閾値に到達したら早期終了"""
        controller = AntiAILoopController(max_loops=5, score_threshold=90.0)
        result = controller.run_sync(AI_TEXT)
        assert result.converged is True
        assert result.iterations <= 5

    def test_stops_when_no_violations(self) -> None:
        """違反ゼロで終了"""
        controller = AntiAILoopController(max_loops=5, score_threshold=90.0)
        result = controller.run_sync(CLEAN_TEXT)
        assert result.converged is True
        assert result.iterations == 0

    def test_respects_max_loops(self) -> None:
        """最大ループ数を守って終了"""
        controller = AntiAILoopController(max_loops=2, score_threshold=100.0)
        result = controller.run_sync(AI_TEXT)
        assert result.iterations <= 2

    def test_history_records_each_iteration(self) -> None:
        """各イテレーションが記録される"""
        controller = AntiAILoopController(max_loops=3, score_threshold=90.0)
        result = controller.run_sync(AI_TEXT)
        assert len(result.history) == result.iterations
        for h in result.history:
            assert h.iteration > 0
            assert h.violations_found >= 0
            assert h.violations_corrected >= 0

    def test_empty_text_returns_clean(self) -> None:
        """空テキストはスコア100で終了"""
        controller = AntiAILoopController()
        result = controller.run_sync(EMPTY_TEXT)
        assert result.final_score == 100.0
        assert result.converged is True
        assert result.iterations == 0

    def test_output_score_improves(self) -> None:
        """修正後のスコアが修正前より高くなる"""
        controller = AntiAILoopController(max_loops=3, score_threshold=90.0)
        result = controller.run_sync(AI_TEXT)
        for h in result.history:
            assert h.output_score >= h.input_score

    def test_iterations_increments(self) -> None:
        """イテレーション回数が正しくカウントされる"""
        controller = AntiAILoopController(max_loops=5, score_threshold=95.0)
        result = controller.run_sync(AI_TEXT)
        if result.iterations > 0:
            assert result.history[0].iteration == 1
            if len(result.history) > 1:
                assert result.history[1].iteration == 2

    def test_final_score_matches_last_output_score(self) -> None:
        """最終スコアが最後の出力スコアと一致する"""
        controller = AntiAILoopController(max_loops=3, score_threshold=90.0)
        result = controller.run_sync(AI_TEXT)
        if result.history:
            assert result.final_score == result.history[-1].output_score

    def test_to_dict(self) -> None:
        """to_dict() が正しく動作"""
        controller = AntiAILoopController()
        result = controller.run_sync(CLEAN_TEXT)
        d = result.to_dict()
        assert "text" in d
        assert "final_score" in d
        assert "iterations" in d
        assert "converged" in d
        assert "history" in d
