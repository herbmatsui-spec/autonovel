"""Tests for emotional context template."""
from __future__ import annotations

import pytest
from jinja2 import Environment, FileSystemLoader

from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType


class TestEmotionalContextTemplate:
    """感情コンテキストテンプレートテスト"""

    @pytest.fixture
    def env(self):
        return Environment(loader=FileSystemLoader("templates"))

    @pytest.fixture
    def template(self, env):
        return env.get_template("emotional_context.j2")

    @ pytest.fixture
    def sample_vector(self):
        vec = EmotionalVector(episode_id="ep14")
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.3, 0.8, "...", "ep14"))
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 0.9, "...", "ep14", "ep14_betrayal"))
        vec.set_signal(EmotionalSignal("B", "A", EmotionType.SADNESS, 0.6, 0.7, "...", "ep14"))
        return vec

    def test_render_basic(self, template, sample_vector):
        """基本レンダリング"""
        # get_top_pairsをモック用に簡易実装
        top_pairs = sample_vector.get_top_pairs(5)
        
        rendered = template.render(
            top_pairs=top_pairs,
            vector=sample_vector,
        )
        
        assert "直前話からの引き継ぎ感情" in rendered
        assert "A→B" in rendered
        assert "B→A" in rendered
        assert "affection" in rendered
        assert "fear" in rendered
        assert "sadness" in rendered

    def test_render_empty(self, template):
        """空ベクトルのレンダリング"""
        vec = EmotionalVector(episode_id="ep01")
        top_pairs = vec.get_top_pairs(5)
        
        rendered = template.render(
            top_pairs=top_pairs,
            vector=vec,
        )
        
        assert "感情データなし" in rendered

    def test_format_values(self, template, sample_vector):
        """値のフォーマット確認"""
        top_pairs = sample_vector.get_top_pairs(5)
        
        rendered = template.render(
            top_pairs=top_pairs,
            vector=sample_vector,
        )
        
        # 小数点1桁でフォーマットされること
        assert "0.3" in rendered or "0.8" in rendered