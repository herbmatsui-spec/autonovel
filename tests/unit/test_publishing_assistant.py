"""Unit tests for Safe Publishing Assistant (Steps 1-12)."""

import pytest

from src.models.publishing_assistant import TargetPlatform, FormattedChapterPayload
from src.services.publishing.content_splitter import ContentSplitter
from src.services.publishing.ai_disclosure_generator import AIDisclosureGenerator
from src.services.publishing.compliance_validator import ComplianceValidator
from src.config.platform_compliance_rules import get_platform_rule


def test_content_splitter_markers():
    """Test extracting foreword, main content, and afterword using markers."""
    raw_text = (
        "【前書き】前話のおさらいです。\n\n"
        "これは本文のテストです。主人公が冒険に出発する。\n\n"
        "【後書き】次回予告：魔王城へ突入！"
    )
    result = ContentSplitter.split_chapter_content(raw_text)
    assert "前話のおさらい" in result["foreword"]
    assert "主人公が冒険" in result["main_content"]
    assert "次回予告" in result["afterword"]


def test_ruby_conversion():
    """Test ruby syntax conversion between kakuyomu and narou."""
    narou_text = "剣聖(けんせい)が立ち上がる。"
    kakuyomu_converted = ContentSplitter.convert_ruby(narou_text, "kakuyomu")
    assert "|剣聖《けんせい》" in kakuyomu_converted

    kakuyomu_text = "|勇者《ゆうしゃ》が現れた。"
    narou_converted = ContentSplitter.convert_ruby(kakuyomu_text, "narou")
    assert "勇者(ゆうしゃ)" in narou_converted


def test_ai_disclosure_generator():
    """Test AI disclosure statements for various platforms."""
    kakuyomu_stmt = AIDisclosureGenerator.generate_disclosure(TargetPlatform.KAKUYOMU)
    assert "AIツール" in kakuyomu_stmt

    narou_stmt = AIDisclosureGenerator.generate_disclosure(TargetPlatform.NAROU)
    assert "AI支援" in narou_stmt

    kindle_stmt = AIDisclosureGenerator.generate_disclosure(TargetPlatform.KINDLE)
    assert "AI-assistance" in kindle_stmt


def test_compliance_validator():
    """Test compliance validation for titles, character counts, and sensitive expressions."""
    # Normal case
    warnings_ok = ComplianceValidator.validate_chapter(
        platform="kakuyomu",
        chapter_title="第1話 平和な日常",
        main_content="あ" * 1000,
        foreword="",
        afterword=""
    )
    # Should contain disclosure recommendation warning
    assert any("タグ" in w or "設定" in w for w in warnings_ok)

    # Title over limit (max 100)
    long_title = "あ" * 105
    warnings_title = ComplianceValidator.validate_chapter(
        platform="kakuyomu",
        chapter_title=long_title,
        main_content="テスト本文",
    )
    assert any("タイトル" in w for w in warnings_title)

    # Sensitive keyword warning for general platform
    warnings_sensitive = ComplianceValidator.validate_chapter(
        platform="narou",
        chapter_title="第2話",
        main_content="ここに過激な性描写を含むテキストが入ります。",
    )
    assert any("警告" in w or "性描写" in w for w in warnings_sensitive)


def test_platform_rules_config():
    """Test platform compliance rule retrieval."""
    rule = get_platform_rule("kakuyomu")
    assert rule.max_chapter_chars == 100000
    assert rule.max_title_chars == 100
    assert rule.requires_ai_disclosure is True
