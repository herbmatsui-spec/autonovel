"""Tests for final_writing_prompt emotional context injection."""
from __future__ import annotations

import pytest
from jinja2 import Environment, FileSystemLoader


class TestFinalWritingPrompt:
    """最終執筆プロンプトテンプレートテスト"""

    @pytest.fixture
    def env(self):
        return Environment(loader=FileSystemLoader("prompts/templates"))

    @pytest.fixture
    def template(self, env):
        return env.get_template("narrative/final_writing_prompt.j2")

    def test_emotional_context_injected(self, template):
        """感情コンテキストが注入されること"""
        rendered = template.render(
            emotional_context="A→B: 恐怖(0.8) [原因: ep14裏切り]",
            quota_inst="文字数指示",
            show_tell_inst="",
            forbidden_inst="",
            hook_inst="",
            assertion_inst="",
            char_static_ctx="",
            char_dynamic_ctx="",
            prev_ctx="",
        )
        
        assert "直前話からの引き継ぎ感情" in rendered
        assert "A→B: 恐怖(0.8) [原因: ep14裏切り]" in rendered

    def test_emotional_context_omitted_when_empty(self, template):
        """空の場合はセクションごと出力されない"""
        rendered = template.render(
            emotional_context="",
            quota_inst="文字数指示",
            show_tell_inst="",
            forbidden_inst="",
            hook_inst="",
            assertion_inst="",
            char_static_ctx="",
            char_dynamic_ctx="",
            prev_ctx="",
        )
        
        assert "直前話からの引き継ぎ感情" not in rendered

    def test_emotional_context_none_when_missing(self, template):
        """変数がない場合も出力されない"""
        rendered = template.render(
            quota_inst="文字数指示",
            show_tell_inst="",
            forbidden_inst="",
            hook_inst="",
            assertion_inst="",
            char_static_ctx="",
            char_dynamic_ctx="",
            prev_ctx="",
        )
        
        assert "直前話からの引き継ぎ感情" not in rendered